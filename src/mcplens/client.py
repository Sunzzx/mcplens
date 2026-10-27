from __future__ import annotations

import asyncio
import json
import shlex
import time
from typing import Any, Dict, List, Optional, Tuple

from mcplens.models import (
    PromptArgument,
    PromptDefinition,
    ResourceDefinition,
    ServerInfo,
    ToolDefinition,
    ToolParameter,
)
from mcplens.token_estimator import estimate_tool_tokens


class MCPError(Exception):
    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"MCP Error [{code}]: {message}")
        self.code = code
        self.message = message
        self.data = data


class MCPClient:
    """
    High-performance, async JSON-RPC 2.0 client for MCP servers over stdio subprocess.
    """

    def __init__(self, command: str, env: Optional[Dict[str, str]] = None, timeout: float = 15.0):
        self.command = command
        self.env = env
        self.timeout = timeout
        self.process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: Dict[int, asyncio.Future] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self.server_info: Optional[ServerInfo] = None

    async def __aenter__(self) -> MCPClient:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        args = shlex.split(self.command)
        if not args:
            raise ValueError("Command cannot be empty")
        self.process = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env,
        )
        self._reader_task = asyncio.create_task(self._read_stdout())

    async def _read_stdout(self):
        if not self.process or not self.process.stdout:
            return
        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            raw = line.decode().strip()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            # Check if this is a response to a pending request
            msg_id = msg.get("id")
            if msg_id in self._pending_requests:
                fut = self._pending_requests.pop(msg_id)
                if not fut.done():
                    if "error" in msg:
                        err = msg["error"]
                        fut.set_exception(
                            MCPError(
                                code=err.get("code", -32000),
                                message=err.get("message", "Unknown error"),
                                data=err.get("data"),
                            )
                        )
                    else:
                        fut.set_result(msg.get("result", {}))

    async def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.process or not self.process.stdin or self.process.returncode is not None:
            raise RuntimeError("Server process is not running")

        self._request_id += 1
        req_id = self._request_id
        payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_requests[req_id] = fut

        data = (json.dumps(payload) + "\n").encode()
        self.process.stdin.write(data)
        await self.process.stdin.drain()

        try:
            return await asyncio.wait_for(fut, timeout=self.timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"MCP request '{method}' timed out after {self.timeout}s")

    async def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        if not self.process or not self.process.stdin or self.process.returncode is not None:
            return
        payload: Dict[str, Any] = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            payload["params"] = params
        data = (json.dumps(payload) + "\n").encode()
        self.process.stdin.write(data)
        await self.process.stdin.drain()

    async def initialize(self) -> ServerInfo:
        t0 = time.perf_counter()
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "mcplens",
                "version": "0.1.0",
            },
        }
        result = await self._send_request("initialize", params)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Send initialized notification
        await self._send_notification("notifications/initialized")

        sinfo = result.get("serverInfo", {})
        self.server_info = ServerInfo(
            name=sinfo.get("name", "unknown-server"),
            version=sinfo.get("version", "0.0.0"),
            protocol_version=result.get("protocolVersion", "2024-11-05"),
            capabilities=result.get("capabilities", {}),
            handshake_latency_ms=round(elapsed_ms, 2),
        )
        return self.server_info

    async def ping(self) -> float:
        t0 = time.perf_counter()
        await self._send_request("ping", {})
        return (time.perf_counter() - t0) * 1000.0

    async def list_tools(self) -> List[ToolDefinition]:
        result = await self._send_request("tools/list", {})
        raw_tools = result.get("tools", [])
        tool_defs = []
        for t in raw_tools:
            name = t.get("name", "unnamed")
            desc = t.get("description", "")
            schema = t.get("inputSchema", {})
            properties = schema.get("properties", {})
            required_props = set(schema.get("required", []))

            params = []
            for p_name, p_schema in properties.items():
                params.append(
                    ToolParameter(
                        name=p_name,
                        type=p_schema.get("type", "any"),
                        description=p_schema.get("description"),
                        required=p_name in required_props,
                        default=p_schema.get("default"),
                        enum=p_schema.get("enum"),
                    )
                )

            tokens = estimate_tool_tokens(name, desc, schema)
            tool_defs.append(
                ToolDefinition(
                    name=name,
                    description=desc,
                    input_schema=schema,
                    parameters=params,
                    estimated_tokens=tokens,
                )
            )
        return tool_defs

    async def list_resources(self) -> List[ResourceDefinition]:
        try:
            result = await self._send_request("resources/list", {})
            raw = result.get("resources", [])
            return [
                ResourceDefinition(
                    uri=r.get("uri", ""),
                    name=r.get("name", ""),
                    description=r.get("description"),
                    mime_type=r.get("mimeType"),
                )
                for r in raw
            ]
        except Exception:
            return []

    async def list_prompts(self) -> List[PromptDefinition]:
        try:
            result = await self._send_request("prompts/list", {})
            raw = result.get("prompts", [])
            prompts = []
            for p in raw:
                args = [
                    PromptArgument(
                        name=a.get("name", ""),
                        description=a.get("description"),
                        required=a.get("required", False),
                    )
                    for a in p.get("arguments", [])
                ]
                prompts.append(
                    PromptDefinition(
                        name=p.get("name", ""),
                        description=p.get("description"),
                        arguments=args,
                    )
                )
            return prompts
        except Exception:
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        t0 = time.perf_counter()
        result = await self._send_request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return result, elapsed_ms

    async def close(self):
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None

        if self.process:
            if self.process.stdin:
                try:
                    self.process.stdin.close()
                    await self.process.stdin.wait_closed()
                except Exception:
                    pass
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

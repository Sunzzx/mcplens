import json
import sys
from typing import Any, Dict

MOCK_TOOLS = [
    {
        "name": "calculate",
        "description": "Safely evaluate mathematical expressions containing basic arithmetic.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to calculate, e.g. '42 * 2'",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "echo",
        "description": "Echo back the provided message with timestamp metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The text string to echo back.",
                }
            },
            "required": ["message"],
        },
    },
    {
        "name": "get_weather",
        "description": "Retrieve current meteorological conditions for a given city location.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Target city or metropolitan area name.",
                },
                "units": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                    "description": "Temperature measurement scale.",
                },
            },
            "required": ["city"],
        },
    },
    {
        "name": "flawed_tool",
        "description": "short",
        "inputSchema": {
            "type": "object",
            "properties": {
                "items_list": {
                    "type": "array",
                },
                "undescribed_param": {
                    "type": "string",
                },
            },
        },
    },
]

MOCK_RESOURCES = [
    {
        "uri": "system://status",
        "name": "System Status",
        "description": "Live mock cluster health report",
        "mimeType": "application/json",
    }
]

MOCK_PROMPTS = [
    {
        "name": "review_code",
        "description": "Prompt template for deep code auditing",
        "arguments": [
            {"name": "language", "description": "Source programming language", "required": True}
        ],
    }
]


def handle_request(req: Dict[str, Any]) -> Dict[str, Any]:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "mcplens-mock-server",
                    "version": "1.0.0",
                },
                "capabilities": {
                    "tools": {"listChanged": True},
                    "resources": {"subscribe": False},
                    "prompts": {"listChanged": False},
                },
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MOCK_TOOLS}}

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": MOCK_RESOURCES}}

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": MOCK_PROMPTS}}

    if method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        if tool_name == "calculate":
            expr = args.get("expression", "0")
            try:
                # Safe evaluation restricted to numbers and math operators
                allowed = set("0123456789+-*/. ()")
                if not all(c in allowed for c in expr):
                    raise ValueError("Forbidden characters in expression")
                val = eval(expr, {"__builtins__": None}, {})
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Result: {val}"}]},
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Calculation error: {e}"},
                }
        elif tool_name == "echo":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": f"Echo: {args.get('message', '')}"}]},
            }
        elif tool_name == "get_weather":
            city = args.get("city", "Unknown")
            units = args.get("units", "celsius")
            temp = 22 if units == "celsius" else 71.6
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": f"Weather in {city}: Sunny, {temp}° {units.capitalize()}"}
                    ]
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"},
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method '{method}' not found"},
    }


def run_mock_server_loop():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            if "id" not in msg:
                # Notification
                continue
            resp = handle_request(msg)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_mock_server_loop()

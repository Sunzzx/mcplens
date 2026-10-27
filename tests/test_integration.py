import sys
import pytest
from mcplens.client import MCPClient
from mcplens.benchmarker import run_benchmark

PYTHON_CMD = sys.executable
SERVER_CMD = f"{PYTHON_CMD} -m mcplens.mock_server"


@pytest.mark.asyncio
async def test_client_handshake_and_inventory():
    async with MCPClient(command=SERVER_CMD, timeout=5.0) as client:
        info = await client.initialize()
        assert info.name == "mcplens-mock-server"
        assert info.version == "1.0.0"
        assert "tools" in info.capabilities

        ping_lat = await client.ping()
        assert ping_lat >= 0.0

        tools = await client.list_tools()
        assert len(tools) >= 4
        tool_names = [t.name for t in tools]
        assert "calculate" in tool_names
        assert "echo" in tool_names
        assert "get_weather" in tool_names

        resources = await client.list_resources()
        assert len(resources) >= 1
        assert resources[0].uri == "system://status"

        prompts = await client.list_prompts()
        assert len(prompts) >= 1
        assert prompts[0].name == "review_code"


@pytest.mark.asyncio
async def test_client_call_tools():
    async with MCPClient(command=SERVER_CMD, timeout=5.0) as client:
        await client.initialize()

        # Call calculate
        res, latency = await client.call_tool(
            "calculate", {"expression": "14 * 3 + 2"}
        )
        assert latency >= 0.0
        content = res.get("content", [{}])[0].get("text", "")
        assert "Result: 44" in content

        # Call echo
        res_echo, _ = await client.call_tool(
            "echo", {"message": "mcplens-unit-test"}
        )
        content_echo = res_echo.get("content", [{}])[0].get("text", "")
        assert "Echo: mcplens-unit-test" in content_echo


@pytest.mark.asyncio
async def test_benchmark_runner():
    res = await run_benchmark(
        command=SERVER_CMD,
        iterations=5,
        timeout=5.0,
    )
    assert res.iterations == 5
    assert res.successful_calls == 5
    assert res.failed_calls == 0
    assert res.requests_per_second > 0.0

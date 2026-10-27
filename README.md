# mcplens 🔍

[![CI](https://github.com/Sunzzx/mcplens/actions/workflows/ci.yml/badge.svg)](https://github.com/Sunzzx/mcplens/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**High-speed diagnostic, auditing, and profiling toolkit for Model Context Protocol (MCP) servers.**

As LLM agents increasingly rely on MCP (Model Context Protocol) to interact with external tools and data, subtle issues in MCP server implementations often go unnoticed: bloated token schemas that blow through context windows, malformed JSON schemas that cause tool-call hallucinations, missing parameter descriptions, breaking schema mutations across versions, and high latency bottlenecks.

`mcplens` gives agent developers, tool creators, and AI infrastructure engineers a unified CLI and SDK to inspect, audit, profile, snapshot, and regression-test MCP servers locally and in CI/CD pipelines.

---

## Key Features

- ⚡ **Instant Protocol Probing**: Fast handshake negotiation, latency measurement, and server capability discovery over standard stdio subprocesses.
- 📊 **Deep Context & Token Footprint Profiling**: Calculates accurate BPE token footprints for every tool schema and prompt injected into LLM context windows.
- 🛡️ **Autonomous Schema Auditing**: Comprehensive quality audit checking for JSON Schema compliance, missing descriptions, unbounded array types, deep nesting, and token bloat with an automated letter grade (A+ through F).
- ⏱️ **Latency & Throughput Benchmarking**: Profile round-trip latency percentiles (min, mean, median p50, p95, p99, max) and throughput (req/s) under sustained tool call load.
- 📸 **Schema Snapshotting & CI Regression Diffing**: Detect breaking changes, parameter type mutations, and removals between schema versions or live servers.
- 🧪 **Built-in Mock Server & Validation Engine**: Client-side JSON Schema parameter validation before tool execution with zero external runtime dependencies.

---

## Installation

Install via `uv` or `pip`:

```bash
uv tool install mcplens
# or
pip install mcplens
```

Or run directly with `uvx`:

```bash
uvx mcplens --help
```

---

## CLI Quickstart

### 1. Probe an MCP Server
Verify server handshake, protocol negotiation, and baseline round-trip latency:

```bash
mcplens probe "npx -y @modelcontextprotocol/server-everything"
```

### 2. Inspect Exposed Tools, Prompts, and Context Footprints
Deep inspection of all tools, input schemas, parameter requirements, and calculated token costs:

```bash
mcplens inspect "python -m my_mcp_server"
```

### 3. Audit Server Schemas for LLM Quality
Audit schemas against best practices for LLM agent function-calling. Fails with non-zero exit code if grade falls below `--min-grade`:

```bash
mcplens audit "python -m my_mcp_server" --min-grade B
```

### 4. Benchmark Execution Latency and Throughput
Benchmark latency distribution (p50, p95, p99) and requests/sec over N iterations:

```bash
mcplens bench "python -m my_mcp_server" --tool calculate --args '{\"expr\": \"2+2\"}' -n 50
```

### 5. Snapshot and Diff for Breaking Changes in CI
Prevent unexpected breaking changes to agent tool interfaces:

```bash
# In CI: capture baseline schema
mcplens snapshot "python -m my_mcp_server" -o schema.v1.json

# Diff new branch against baseline
mcplens diff schema.v1.json "python -m my_mcp_server"
```

### 6. Safely Invoke Tools with Client-side Schema Validation

```bash
mcplens call "python -m my_mcp_server" --tool get_weather --args '{\"city\": \"San Francisco\"}'
```

---

## Python SDK

`mcplens` can also be integrated directly into your Python test suites and evaluation harnesses:

```python
import asyncio
from mcplens import MCPClient, audit_tools, run_benchmark

async def main():
    # Connect to MCP server over stdio
    async with MCPClient(command="python -m my_server") as client:
        info = await client.initialize()
        tools = await client.list_tools()
        
        # Run schema audit
        report = audit_tools(server_name=info.name, tools=tools)
        print(f"Quality Grade: {report.grade} ({report.quality_score}/100)")
        
        # Execute tool
        result, latency_ms = await client.call_tool("fetch_data", {"id": 123})
        print(f"Execution completed in {latency_ms:.2f}ms")

asyncio.run(main())
```

---

## Architecture

```
+-------------------------------------------------------------+
|                          mcplens CLI                        |
|     [probe]  [inspect]  [audit]  [bench]  [diff]  [call]    |
+-------------------------------------------------------------+
                                |
     +--------------------------+--------------------------+
     |                          |                          |
     v                          v                          v
+------------------+   +-------------------+   +-------------------+
|    MCPClient     |   |   Auditor Engine  |   |    Benchmarker    |
|  JSON-RPC 2.0    |   | JSON Schema Check |   | Latency (p50/p95) |
|  Stdio Transport |   | Token Estimator   |   | Throughput (req/s)|
+------------------+   +-------------------+   +-------------------+
```

---

## Testing

Run the comprehensive test suite with `pytest`:

```bash
uv run pytest -v
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

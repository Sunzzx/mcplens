from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import jsonschema
from jsonschema.exceptions import ValidationError
import typer
from rich.console import Console

from mcplens.auditor import audit_tools
from mcplens.benchmarker import run_benchmark
from mcplens.client import MCPClient, MCPError
from mcplens.differ import diff_tool_lists
from mcplens.formatter import (
    print_audit_report,
    print_benchmark_report,
    print_diff_report,
    print_probe_panel,
    print_prompts_table,
    print_resources_table,
    print_tools_table,
)
from mcplens.models import ToolDefinition

app = typer.Typer(
    name="mcplens",
    help="High-speed diagnostic, auditing, and profiling toolkit for Model Context Protocol (MCP) servers.",
    add_completion=False,
)
console = Console()


def _run_async(coro):
    return asyncio.run(coro)


@app.command()
def probe(
    command: str = typer.Argument(..., help="Shell command to run the MCP server (e.g. 'python server.py')"),
    timeout: float = typer.Option(10.0, "--timeout", "-t", help="Handshake timeout in seconds"),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON instead of styled panel"),
):
    """Test MCP server handshake, negotiate protocol, and measure latency."""
    async def _probe():
        async with MCPClient(command=command, timeout=timeout) as client:
            info = await client.initialize()
            if as_json:
                print(info.model_dump_json(indent=2))
            else:
                print_probe_panel(info)

    try:
        _run_async(_probe())
    except Exception as e:
        console.print(f"[bold red]Handshake failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def inspect(
    command: str = typer.Argument(..., help="Shell command to run the MCP server"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Timeout in seconds"),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON instead of tables"),
):
    """Deep inspection of exposed tools, parameters, resources, prompts, and token footprints."""
    async def _inspect():
        async with MCPClient(command=command, timeout=timeout) as client:
            info = await client.initialize()
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()

            if as_json:
                payload = {
                    "server": info.model_dump(),
                    "tools": [t.model_dump() for t in tools],
                    "resources": [r.model_dump() for r in resources],
                    "prompts": [p.model_dump() for p in prompts],
                }
                print(json.dumps(payload, indent=2))
            else:
                print_probe_panel(info)
                print_tools_table(tools)
                if resources:
                    print_resources_table(resources)
                if prompts:
                    print_prompts_table(prompts)

    try:
        _run_async(_inspect())
    except Exception as e:
        console.print(f"[bold red]Inspection failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def audit(
    command: str = typer.Argument(..., help="Shell command to run the MCP server"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Timeout in seconds"),
    min_grade: Optional[str] = typer.Option(None, "--min-grade", help="Minimum acceptable grade (A+, A, B, C, D)"),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON audit report"),
):
    """Audit MCP server schemas for LLM quality, token efficiency, and compliance defects."""
    async def _audit():
        async with MCPClient(command=command, timeout=timeout) as client:
            info = await client.initialize()
            tools = await client.list_tools()
            report = audit_tools(server_name=info.name, tools=tools)

            if as_json:
                print(report.model_dump_json(indent=2))
            else:
                print_audit_report(report)

            if min_grade:
                grade_order = ["A+", "A", "B", "C", "D", "F"]
                min_idx = grade_order.index(min_grade.upper()) if min_grade.upper() in grade_order else 2
                cur_idx = grade_order.index(report.grade)
                if cur_idx > min_idx:
                    console.print(f"[bold red]Audit failed:[/bold red] Grade {report.grade} is below threshold {min_grade}")
                    sys.exit(1)

    try:
        _run_async(_audit())
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[bold red]Audit failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def bench(
    command: str = typer.Argument(..., help="Shell command to run the MCP server"),
    tool: Optional[str] = typer.Option(None, "--tool", help="Tool name to benchmark (omit for ping)"),
    args: str = typer.Option("{}", "--args", help="JSON string of arguments for tool call"),
    iterations: int = typer.Option(20, "--iterations", "-n", help="Number of benchmark cycles"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Request timeout"),
    as_json: bool = typer.Option(False, "--json", help="Output raw JSON benchmark results"),
):
    """Profile MCP server latency distribution and throughput over N iterations."""
    tool_args = json.loads(args) if args else {}
    async def _bench():
        res = await run_benchmark(
            command=command,
            tool_name=tool,
            tool_args=tool_args,
            iterations=iterations,
            timeout=timeout,
        )
        if as_json:
            print(res.model_dump_json(indent=2))
        else:
            print_benchmark_report(res)

    try:
        _run_async(_bench())
    except Exception as e:
        console.print(f"[bold red]Benchmark failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def call(
    command: str = typer.Argument(..., help="Shell command to run the MCP server"),
    tool: str = typer.Option(..., "--tool", help="Tool name to invoke"),
    args: str = typer.Option("{}", "--args", help="JSON string of arguments"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Timeout"),
):
    """Invoke an MCP tool with client-side JSON Schema validation."""
    try:
        tool_args = json.loads(args)
    except Exception as e:
        console.print(f"[bold red]Invalid arguments JSON:[/bold red] {e}")
        raise typer.Exit(code=1)

    async def _call():
        async with MCPClient(command=command, timeout=timeout) as client:
            await client.initialize()
            tools = await client.list_tools()
            matched = next((t for t in tools if t.name == tool), None)
            if not matched:
                console.print(f"[bold red]Error:[/bold red] Tool '{tool}' not found on server.")
                sys.exit(1)

            # Client-side validation
            schema = matched.input_schema
            try:
                jsonschema.validate(instance=tool_args, schema=schema)
            except ValidationError as val_err:
                console.print(f"[bold red]Schema validation failed:[/bold red] {val_err.message}")
                sys.exit(2)

            # Dispatch
            result, elapsed_ms = await client.call_tool(tool, tool_args)
            console.print(f"[green]✓ Tool executed in {elapsed_ms:.2f} ms[/green]\n")
            print(json.dumps(result, indent=2))

    try:
        _run_async(_call())
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[bold red]Execution error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def snapshot(
    command: str = typer.Argument(..., help="Shell command to run the MCP server"),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSON snapshot file path"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Timeout"),
):
    """Save a complete MCP server schema snapshot to JSON for CI/CD regression testing."""
    async def _snap():
        async with MCPClient(command=command, timeout=timeout) as client:
            info = await client.initialize()
            tools = await client.list_tools()
            payload = {
                "server": info.model_dump(),
                "tools": [t.model_dump() for t in tools],
            }
            output.write_text(json.dumps(payload, indent=2))
            console.print(f"[green]✓ Snapshot saved to {output} ({len(tools)} tools recorded)[/green]")

    try:
        _run_async(_snap())
    except Exception as e:
        console.print(f"[bold red]Snapshot error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def diff(
    target_a: str = typer.Argument(..., help="First server command or JSON snapshot path"),
    target_b: str = typer.Argument(..., help="Second server command or JSON snapshot path"),
    timeout: float = typer.Option(15.0, "--timeout", "-t", help="Timeout"),
    as_json: bool = typer.Option(False, "--json", help="Output diff as JSON"),
):
    """Diff two MCP servers or schema snapshots to detect breaking changes and additions."""
    async def _get_tools(target: str) -> list[ToolDefinition]:
        path = Path(target)
        if path.exists() and path.is_file():
            data = json.loads(path.read_text())
            raw_tools = data.get("tools", [])
            return [ToolDefinition(**t) for t in raw_tools]
        else:
            async with MCPClient(command=target, timeout=timeout) as client:
                await client.initialize()
                return await client.list_tools()

    async def _run_diff():
        tools_a = await _get_tools(target_a)
        tools_b = await _get_tools(target_b)
        rep = diff_tool_lists(target_a, tools_a, target_b, tools_b)

        if as_json:
            print(rep.model_dump_json(indent=2))
        else:
            print_diff_report(rep)

        if not rep.is_compatible:
            sys.exit(1)

    try:
        _run_async(_run_diff())
    except SystemExit:
        raise
    except Exception as e:
        console.print(f"[bold red]Diff failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def mock():
    """Launch the built-in mock MCP server on standard I/O."""
    from mcplens.mock_server import run_mock_server_loop
    run_mock_server_loop()


if __name__ == "__main__":
    app()

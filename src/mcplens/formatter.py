from __future__ import annotations

from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mcplens.models import (
    AuditReport,
    BenchmarkResult,
    DiffReport,
    PromptDefinition,
    ResourceDefinition,
    ServerInfo,
    ToolDefinition,
)

console = Console()


def print_probe_panel(info: ServerInfo):
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan")
    grid.add_column()

    grid.add_row("Server Name:", info.name)
    grid.add_row("Server Version:", info.version)
    grid.add_row("Protocol Version:", info.protocol_version)
    grid.add_row("Handshake Latency:", f"{info.handshake_latency_ms:.2f} ms")
    
    caps = []
    for cap, val in info.capabilities.items():
        if val is True or isinstance(val, dict):
            caps.append(f"[green]{cap}[/green]")
    grid.add_row("Capabilities:", ", ".join(caps) if caps else "none")

    console.print(
        Panel(
            grid,
            title="[bold green]✓ MCP Server Active[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def print_tools_table(tools: List[ToolDefinition]):
    table = Table(title="[bold]Discovered Tools[/bold]", border_style="bright_black")
    table.add_column("Tool Name", style="bold cyan")
    table.add_column("Description", style="white")
    table.add_column("Parameters", justify="center", style="yellow")
    table.add_column("Required", justify="center", style="red")
    table.add_column("Est. Tokens", justify="right", style="magenta")

    total_tokens = 0
    for t in tools:
        total_tokens += t.estimated_tokens
        req_count = sum(1 for p in t.parameters if p.required)
        short_desc = (t.description[:60] + "...") if len(t.description) > 60 else t.description
        table.add_row(
            t.name,
            short_desc or "[dim](no description)[/dim]",
            str(len(t.parameters)),
            str(req_count),
            f"{t.estimated_tokens:,}",
        )

    table.caption = f"Total: {len(tools)} tools | Context Footprint: {total_tokens:,} tokens"
    console.print(table)


def print_resources_table(resources: List[ResourceDefinition]):
    if not resources:
        return
    table = Table(title="[bold]Exposed Resources[/bold]", border_style="bright_black")
    table.add_column("Name", style="bold cyan")
    table.add_column("URI", style="green")
    table.add_column("MIME Type", style="yellow")
    table.add_column("Description", style="dim white")
    for r in resources:
        table.add_row(r.name, r.uri, r.mime_type or "-", r.description or "-")
    console.print(table)


def print_prompts_table(prompts: List[PromptDefinition]):
    if not prompts:
        return
    table = Table(title="[bold]Exposed Prompts[/bold]", border_style="bright_black")
    table.add_column("Prompt Name", style="bold cyan")
    table.add_column("Description", style="white")
    table.add_column("Arguments", justify="center", style="yellow")
    for p in prompts:
        args_str = ", ".join(a.name for a in p.arguments) if p.arguments else "none"
        table.add_row(p.name, p.description or "-", args_str)
    console.print(table)


def print_audit_report(report: AuditReport):
    grade_colors = {
        "A+": "bold green",
        "A": "green",
        "B": "yellow",
        "C": "bright_yellow",
        "D": "red",
        "F": "bold red",
    }
    color = grade_colors.get(report.grade, "white")

    score_header = f"[{color}]GRADE: {report.grade} ({report.quality_score}/100)[/{color}]"
    header_table = Table.grid(padding=(0, 2))
    header_table.add_column(style="bold")
    header_table.add_column()
    header_table.add_row("Server Name:", report.server_name)
    header_table.add_row("Quality Rating:", score_header)
    header_table.add_row("Total Tools:", str(report.total_tools))
    header_table.add_row("Token Footprint:", f"{report.total_tokens:,} tokens")

    console.print(
        Panel(
            header_table,
            title="[bold cyan]MCP Protocol & Schema Quality Audit[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    if not report.findings:
        console.print("[bold green]✓ Zero defects found! Server schemas follow best practices.[/bold green]\n")
        return

    table = Table(title="[bold]Audit Findings & Recommendations[/bold]", border_style="bright_black")
    table.add_column("Sev", justify="center")
    table.add_column("Tool", style="cyan")
    table.add_column("Code", style="yellow")
    table.add_column("Finding", style="white")
    table.add_column("Remediation", style="dim green")

    for f in report.findings:
        sev_text = (
            "[bold red]CRIT[/bold red]"
            if f.severity == "critical"
            else "[yellow]WARN[/yellow]"
            if f.severity == "warning"
            else "[blue]INFO[/blue]"
        )
        table.add_row(
            sev_text,
            f.tool_name or "*",
            f.code,
            f.message,
            f.remediation,
        )
    console.print(table)


def print_benchmark_report(bench: BenchmarkResult):
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold cyan")
    grid.add_column()

    success_pct = (bench.successful_calls / bench.iterations) * 100.0
    grid.add_row("Iterations:", f"{bench.iterations} calls ({success_pct:.1f}% success)")
    grid.add_row("Throughput:", f"[bold green]{bench.requests_per_second:.2f} req/s[/bold green]")
    grid.add_row("Min Latency:", f"{bench.min_latency_ms:.2f} ms")
    grid.add_row("Mean Latency:", f"{bench.mean_latency_ms:.2f} ms")
    grid.add_row("Median (p50):", f"{bench.median_latency_ms:.2f} ms")
    grid.add_row("p95 Latency:", f"{bench.p95_latency_ms:.2f} ms")
    grid.add_row("p99 Latency:", f"{bench.p99_latency_ms:.2f} ms")
    grid.add_row("Max Latency:", f"{bench.max_latency_ms:.2f} ms")
    grid.add_row("Payload Transferred:", f"{bench.total_payload_bytes:,} bytes")

    console.print(
        Panel(
            grid,
            title="[bold cyan]Performance & Latency Benchmark[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )


def print_diff_report(report: DiffReport):
    compat_str = (
        "[bold green]✓ BACKWARD COMPATIBLE[/bold green]"
        if report.is_compatible
        else "[bold red]✗ BREAKING CHANGES DETECTED[/bold red]"
    )
    console.print(f"\nComparing [cyan]{report.target_a}[/cyan] -> [cyan]{report.target_b}[/cyan]")
    console.print(f"Compatibility Verdict: {compat_str}\n")

    if not report.changes:
        console.print("[dim]No differences detected between schemas.[/dim]\n")
        return

    table = Table(title="[bold]Schema Changes[/bold]", border_style="bright_black")
    table.add_column("Category", justify="center")
    table.add_column("Type", style="cyan")
    table.add_column("Target", style="bold white")
    table.add_column("Details", style="white")

    for c in report.changes:
        cat_style = (
            "[bold red]BREAKING[/bold red]"
            if c.category == "breaking"
            else "[green]ADDED[/green]"
            if c.category == "addition"
            else "[yellow]CHANGED[/yellow]"
        )
        table.add_row(cat_style, c.target_type, c.target_name, c.detail)
    console.print(table)

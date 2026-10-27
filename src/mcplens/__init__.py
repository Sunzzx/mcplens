from mcplens.client import MCPClient, MCPError
from mcplens.auditor import audit_tools
from mcplens.benchmarker import run_benchmark
from mcplens.differ import diff_tool_lists
from mcplens.models import (
    AuditFinding,
    AuditReport,
    BenchmarkResult,
    DiffChange,
    DiffReport,
    ServerInfo,
    ToolDefinition,
)

__version__ = "0.1.0"
__all__ = [
    "MCPClient",
    "MCPError",
    "audit_tools",
    "run_benchmark",
    "diff_tool_lists",
    "AuditFinding",
    "AuditReport",
    "BenchmarkResult",
    "DiffChange",
    "DiffReport",
    "ServerInfo",
    "ToolDefinition",
]

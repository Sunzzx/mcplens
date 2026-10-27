from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ServerInfo(BaseModel):
    name: str
    version: str
    protocol_version: str = "2024-11-05"
    capabilities: Dict[str, Any] = Field(default_factory=dict)
    handshake_latency_ms: float = 0.0


class ToolParameter(BaseModel):
    name: str
    type: str = "any"
    description: Optional[str] = None
    required: bool = False
    default: Any = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseModel):
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    parameters: List[ToolParameter] = Field(default_factory=list)
    estimated_tokens: int = 0


class ResourceDefinition(BaseModel):
    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class PromptArgument(BaseModel):
    name: str
    description: Optional[str] = None
    required: bool = False


class PromptDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    arguments: List[PromptArgument] = Field(default_factory=list)


class AuditFinding(BaseModel):
    severity: str  # 'critical', 'warning', 'info'
    tool_name: Optional[str] = None
    code: str
    message: str
    remediation: str


class AuditReport(BaseModel):
    server_name: str
    total_tools: int = 0
    total_tokens: int = 0
    quality_score: int = 100  # 0-100
    grade: str = "A+"  # A+, A, B, C, D, F
    findings: List[AuditFinding] = Field(default_factory=list)
    summary: str = ""


class BenchmarkResult(BaseModel):
    iterations: int
    successful_calls: int
    failed_calls: int
    min_latency_ms: float
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    requests_per_second: float
    total_payload_bytes: int


class DiffChange(BaseModel):
    category: str  # 'breaking', 'addition', 'modification', 'deprecation'
    target_type: str  # 'tool', 'resource', 'prompt'
    target_name: str
    detail: str


class DiffReport(BaseModel):
    target_a: str
    target_b: str
    is_compatible: bool = True
    changes: List[DiffChange] = Field(default_factory=list)

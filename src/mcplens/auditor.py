from __future__ import annotations

from typing import Any, Dict, List, Tuple
import jsonschema
from jsonschema.exceptions import SchemaError

from mcplens.models import AuditFinding, AuditReport, ToolDefinition

VALID_JSON_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}


def calculate_schema_depth(schema: Any, current_depth: int = 1) -> int:
    if not isinstance(schema, dict):
        return current_depth
    max_d = current_depth
    for k, v in schema.items():
        if k in ("properties", "patternProperties", "definitions", "$defs") and isinstance(v, dict):
            for sub_k, sub_v in v.items():
                max_d = max(max_d, calculate_schema_depth(sub_v, current_depth + 1))
        elif k in ("items", "additionalProperties") and isinstance(v, dict):
            max_d = max(max_d, calculate_schema_depth(v, current_depth + 1))
    return max_d


def audit_tools(server_name: str, tools: List[ToolDefinition]) -> AuditReport:
    findings: List[AuditFinding] = []
    total_tokens = sum(t.estimated_tokens for t in tools)
    deductions = 0

    for tool in tools:
        # 1. Tool description check
        desc = (tool.description or "").strip()
        if not desc:
            findings.append(
                AuditFinding(
                    severity="critical",
                    tool_name=tool.name,
                    code="MISSING_TOOL_DESC",
                    message=f"Tool '{tool.name}' has no description.",
                    remediation="Provide a clear, concise description explaining when and how the model should use this tool.",
                )
            )
            deductions += 15
        elif len(desc) < 15:
            findings.append(
                AuditFinding(
                    severity="warning",
                    tool_name=tool.name,
                    code="SHORT_TOOL_DESC",
                    message=f"Tool '{tool.name}' description is very short ({len(desc)} chars). Model may misunderstand intent.",
                    remediation="Expand description with intent, input context, and expected output behavior.",
                )
            )
            deductions += 5

        # 2. JSON Schema Draft validity
        schema = tool.input_schema or {}
        try:
            jsonschema.Draft202012Validator.check_schema(schema)
        except SchemaError as err:
            findings.append(
                AuditFinding(
                    severity="critical",
                    tool_name=tool.name,
                    code="INVALID_JSON_SCHEMA",
                    message=f"Tool '{tool.name}' inputSchema is not valid JSON Schema: {err.message}",
                    remediation="Correct the JSON Schema syntax to comply with Draft-07 or Draft 2020-12.",
                )
            )
            deductions += 25

        # 3. Parameters check
        properties = schema.get("properties", {})
        required_props = set(schema.get("required", []))
        
        for p_name, p_schema in properties.items():
            if not isinstance(p_schema, dict):
                continue
            
            p_type = p_schema.get("type")
            if p_type and p_type not in VALID_JSON_TYPES:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        tool_name=tool.name,
                        code="INVALID_PARAM_TYPE",
                        message=f"Parameter '{p_name}' has unrecognized type '{p_type}'.",
                        remediation=f"Use standard JSON Schema types: {', '.join(sorted(VALID_JSON_TYPES))}",
                    )
                )
                deductions += 5

            p_desc = (p_schema.get("description") or "").strip()
            if not p_desc:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        tool_name=tool.name,
                        code="MISSING_PARAM_DESC",
                        message=f"Parameter '{p_name}' in tool '{tool.name}' lacks description.",
                        remediation="Add a description detailing expected format, semantics, and examples.",
                    )
                )
                deductions += 6

            # Check unbounded arrays
            if p_type == "array" and "items" not in p_schema:
                findings.append(
                    AuditFinding(
                        severity="warning",
                        tool_name=tool.name,
                        code="UNBOUNDED_ARRAY",
                        message=f"Array parameter '{p_name}' missing 'items' definition.",
                        remediation="Define 'items': {'type': '...'} to prevent ambiguous array generation by LLMs.",
                    )
                )
                deductions += 5

        # 4. Schema Depth Check
        depth = calculate_schema_depth(schema)
        if depth > 3:
            findings.append(
                AuditFinding(
                    severity="warning",
                    tool_name=tool.name,
                    code="EXCESSIVE_DEPTH",
                    message=f"Tool '{tool.name}' schema has depth {depth} (> 3 levels).",
                    remediation="Flatten nested structures to reduce cognitive load on the LLM.",
                )
            )
            deductions += 8

        # 5. Token bloat
        if tool.estimated_tokens > 750:
            findings.append(
                AuditFinding(
                    severity="warning",
                    tool_name=tool.name,
                    code="TOKEN_BLOAT",
                    message=f"Tool '{tool.name}' consumes {tool.estimated_tokens} tokens in prompt context.",
                    remediation="Streamline schema documentation, reduce enum options, or split into smaller granular tools.",
                )
            )
            deductions += 10

    score = max(0, 100 - deductions)
    if score >= 95:
        grade = "A+"
    elif score >= 88:
        grade = "A"
    elif score >= 78:
        grade = "B"
    elif score >= 65:
        grade = "C"
    elif score >= 50:
        grade = "D"
    else:
        grade = "F"

    summary = f"Audited {len(tools)} tools ({total_tokens} total context tokens). {len(findings)} findings detected."

    return AuditReport(
        server_name=server_name,
        total_tools=len(tools),
        total_tokens=total_tokens,
        quality_score=score,
        grade=grade,
        findings=findings,
        summary=summary,
    )

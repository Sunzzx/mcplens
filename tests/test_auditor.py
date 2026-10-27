from mcplens.auditor import audit_tools
from mcplens.models import ToolDefinition, ToolParameter


def test_audit_tools_clean():
    tools = [
        ToolDefinition(
            name="fetch_logs",
            description="Retrieve and stream system log messages for debugging.",
            input_schema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Target service name to monitor",
                    }
                },
                "required": ["service"],
            },
            parameters=[
                ToolParameter(
                    name="service",
                    type="string",
                    description="Target service name to monitor",
                    required=True,
                )
            ],
            estimated_tokens=50,
        )
    ]
    report = audit_tools("clean-server", tools)
    assert report.grade in ("A+", "A")
    assert report.quality_score >= 90
    assert len(report.findings) == 0


def test_audit_tools_with_defects():
    tools = [
        ToolDefinition(
            name="broken_tool",
            description="",  # missing description
            input_schema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array"},  # unbounded array
                    "query": {"type": "string"},  # missing description
                },
            },
            parameters=[
                ToolParameter(name="tags", type="array", required=False),
                ToolParameter(name="query", type="string", required=False),
            ],
            estimated_tokens=60,
        )
    ]
    report = audit_tools("buggy-server", tools)
    assert report.grade in ("C", "D", "F")
    assert report.quality_score < 80
    codes = [f.code for f in report.findings]
    assert "MISSING_TOOL_DESC" in codes
    assert "UNBOUNDED_ARRAY" in codes
    assert "MISSING_PARAM_DESC" in codes

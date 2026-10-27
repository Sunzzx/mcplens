from mcplens.differ import diff_tool_lists
from mcplens.models import ToolDefinition, ToolParameter


def test_diff_tool_lists_breaking():
    tools_v1 = [
        ToolDefinition(
            name="delete_user",
            description="Delete user account",
            parameters=[ToolParameter(name="user_id", type="string", required=True)],
        )
    ]
    tools_v2 = []  # tool removed

    diff = diff_tool_lists("v1", tools_v1, "v2", tools_v2)
    assert diff.is_compatible is False
    assert len(diff.changes) == 1
    assert diff.changes[0].category == "breaking"


def test_diff_tool_lists_addition():
    tools_v1 = [
        ToolDefinition(
            name="search",
            description="Search documents",
            parameters=[ToolParameter(name="query", type="string", required=True)],
        )
    ]
    tools_v2 = [
        ToolDefinition(
            name="search",
            description="Search documents",
            parameters=[
                ToolParameter(name="query", type="string", required=True),
                ToolParameter(name="limit", type="integer", required=False),  # optional addition
            ],
        )
    ]

    diff = diff_tool_lists("v1", tools_v1, "v2", tools_v2)
    assert diff.is_compatible is True
    assert any(c.category == "addition" for c in diff.changes)

from __future__ import annotations

from typing import Any, Dict, List

from mcplens.models import DiffChange, DiffReport, ToolDefinition


def diff_tool_lists(
    target_a: str,
    tools_a: List[ToolDefinition],
    target_b: str,
    tools_b: List[ToolDefinition],
) -> DiffReport:
    changes: List[DiffChange] = []
    
    map_a = {t.name: t for t in tools_a}
    map_b = {t.name: t for t in tools_b}

    # Detect removed tools (BREAKING)
    for name, tool in map_a.items():
        if name not in map_b:
            changes.append(
                DiffChange(
                    category="breaking",
                    target_type="tool",
                    target_name=name,
                    detail=f"Tool '{name}' removed in target B",
                )
            )

    # Detect added tools (ADDITION)
    for name, tool in map_b.items():
        if name not in map_a:
            changes.append(
                DiffChange(
                    category="addition",
                    target_type="tool",
                    target_name=name,
                    detail=f"New tool '{name}' added with {len(tool.parameters)} parameters",
                )
            )

    # Detect tool modifications
    for name in map_a.keys() & map_b.keys():
        tool_a = map_a[name]
        tool_b = map_b[name]

        if tool_a.description != tool_b.description:
            changes.append(
                DiffChange(
                    category="modification",
                    target_type="tool",
                    target_name=name,
                    detail=f"Tool '{name}' description changed",
                )
            )

        params_a = {p.name: p for p in tool_a.parameters}
        params_b = {p.name: p for p in tool_b.parameters}

        # Check removed parameters
        for p_name in params_a.keys() - params_b.keys():
            changes.append(
                DiffChange(
                    category="breaking",
                    target_type="tool",
                    target_name=name,
                    detail=f"Parameter '{p_name}' removed from tool '{name}'",
                )
            )

        # Check added parameters
        for p_name in params_b.keys() - params_a.keys():
            p = params_b[p_name]
            if p.required:
                changes.append(
                    DiffChange(
                        category="breaking",
                        target_type="tool",
                        target_name=name,
                        detail=f"New REQUIRED parameter '{p_name}' added to tool '{name}'",
                    )
                )
            else:
                changes.append(
                    DiffChange(
                        category="addition",
                        target_type="tool",
                        target_name=name,
                        detail=f"New optional parameter '{p_name}' added to tool '{name}'",
                    )
                )

        # Check parameter type mutations
        for p_name in params_a.keys() & params_b.keys():
            p_a = params_a[p_name]
            p_b = params_b[p_name]
            if p_a.type != p_b.type:
                changes.append(
                    DiffChange(
                        category="breaking",
                        target_type="tool",
                        target_name=name,
                        detail=f"Parameter '{p_name}' in tool '{name}' type changed from '{p_a.type}' to '{p_b.type}'",
                    )
                )
            elif not p_a.required and p_b.required:
                changes.append(
                    DiffChange(
                        category="breaking",
                        target_type="tool",
                        target_name=name,
                        detail=f"Existing parameter '{p_name}' in tool '{name}' changed from optional to REQUIRED",
                    )
                )

    is_compatible = not any(c.category == "breaking" for c in changes)
    return DiffReport(
        target_a=target_a,
        target_b=target_b,
        is_compatible=is_compatible,
        changes=changes,
    )

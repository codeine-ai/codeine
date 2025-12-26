"""
coupling_matrix - Generate class coupling/cohesion matrix.

Shows coupling strength between classes as a matrix visualization.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("coupling_matrix")
@param("classes", list, required=False, default=None, description="List of classes to analyze")
@param("max_classes", int, default=20, description="Maximum classes to include")
@param("threshold", int, default=0, description="Minimum coupling to display")
@param("include_inheritance", bool, default=True, description="Include inheritance in coupling")
@param("format", str, default="markdown", description="Output format: json, markdown, heatmap")
def coupling_matrix() -> Pipeline:
    """
    Generate coupling/cohesion matrix between classes.

    Returns:
        diagram: Formatted coupling matrix
        matrix: Coupling strength data
        classes: Classes analyzed
        summary: Coupling statistics
    """
    # Note: UNION doesn't work in REQL, so we only use method calls for coupling
    # Inheritance coupling would require a separate query
    return (
        reql('''
            SELECT ?callerClassName ?calleeClassName
            WHERE {
                ?caller type {Method} .
                ?caller calls ?callee .
                ?callee type {Method} .
                ?caller definedIn ?callerClass .
                ?callee definedIn ?calleeClass .
                ?callerClass name ?callerClassName .
                ?calleeClass name ?calleeClassName
            }
        ''')
        .select("callerClassName", "calleeClassName")
        .tap(_calculate_coupling)
        .render(format="{format}", renderer=_render_matrix)
        .emit("diagram")
    )


def _calculate_coupling(rows, ctx=None):
    """Calculate coupling matrix from query results."""
    target_classes = None
    max_classes = 20

    if ctx is not None:
        target_classes = ctx.params.get('classes')
        max_classes = ctx.params.get('max_classes', 20)

    # Also store threshold for renderer
    threshold = 0
    if ctx is not None:
        threshold = ctx.params.get('threshold', 0)

    # Collect all classes from method calls
    all_classes = set()
    method_calls = []

    for row in rows:
        # Handle both raw REQL (?key) and post-select (key)
        caller = row.get('callerClassName') or row.get('?callerClassName')
        callee = row.get('calleeClassName') or row.get('?calleeClassName')
        if caller and callee:
            all_classes.add(caller)
            all_classes.add(callee)
            method_calls.append((caller, callee))

    # Filter to target classes if specified
    if target_classes:
        classes = [c for c in target_classes if c in all_classes]
    else:
        classes = list(all_classes)

    # Limit classes
    if len(classes) > max_classes:
        # Keep most coupled classes
        coupling_totals = {}
        for cls in classes:
            total = sum(1 for c, t in method_calls if c == cls or t == cls)
            coupling_totals[cls] = total

        classes = sorted(classes, key=lambda c: coupling_totals.get(c, 0), reverse=True)[:max_classes]

    classes = sorted(classes)

    # Build coupling matrix
    matrix = {cls: {} for cls in classes}

    # Count method call coupling
    for caller, callee in method_calls:
        if caller in classes and callee in classes and caller != callee:
            matrix[caller][callee] = matrix[caller].get(callee, 0) + 1

    return {"matrix": matrix, "classes": classes, "threshold": threshold}


def _render_matrix(data, format):
    """Render coupling matrix in requested format."""
    # Extract from tap result
    if isinstance(data, dict) and '_tap_result' in data:
        data = data['_tap_result']

    if isinstance(data, dict) and 'matrix' in data:
        matrix = data['matrix']
        classes = data['classes']
        threshold = data.get('threshold', 0)
    else:
        return {"error": "Invalid coupling data"}

    # Apply threshold
    if threshold > 0:
        matrix = {
            cls1: {cls2: s for cls2, s in deps.items() if s >= threshold}
            for cls1, deps in matrix.items()
        }

    # Calculate stats
    total_relationships = sum(len(deps) for deps in matrix.values())
    high_coupling = sum(1 for deps in matrix.values() for s in deps.values() if s >= 8)

    if format == "json":
        return {
            "matrix": matrix,
            "classes": classes,
            "total_relationships": total_relationships,
            "high_coupling_count": high_coupling
        }

    if format == "heatmap":
        return _render_heatmap(matrix, classes)

    # Markdown table
    lines = ["# Coupling Matrix", ""]
    lines.append("## Legend")
    lines.append("- Low (1-3): Loose coupling")
    lines.append("- Medium (4-7): Moderate coupling")
    lines.append("- High (8+): Tight coupling - consider refactoring")
    lines.append("")

    if threshold > 0:
        lines.append(f"**Filter**: Showing only coupling >= {threshold}")
        lines.append("")

    # Build table
    header = "| Class |" + "".join(f" {cls[:10]} |" for cls in classes)
    separator = "|-------|" + "|".join("-" * 12 for _ in classes) + "|"

    lines.append(header)
    lines.append(separator)

    for cls1 in classes:
        row = [f"| **{cls1[:10]}**"]
        for cls2 in classes:
            if cls1 == cls2:
                row.append(" - ")
            else:
                strength = matrix.get(cls1, {}).get(cls2, 0)
                if strength == 0:
                    row.append(" . ")
                elif strength >= 8:
                    row.append(f" **{strength}** ")
                elif strength >= 4:
                    row.append(f" *{strength}* ")
                else:
                    row.append(f" {strength} ")
        lines.append("|".join(row) + "|")

    lines.append("")
    lines.append("## Summary")
    lines.append(f"- **Classes analyzed**: {len(classes)}")
    lines.append(f"- **Coupled pairs**: {total_relationships}")
    lines.append(f"- **High coupling pairs**: {high_coupling}")

    if high_coupling > 0:
        lines.append("")
        lines.append("### High Coupling Pairs")
        for cls1 in classes:
            for cls2, strength in matrix.get(cls1, {}).items():
                if strength >= 8:
                    lines.append(f"- `{cls1}` -> `{cls2}`: {strength}")

    return "\n".join(lines)


def _render_heatmap(matrix, classes):
    """Render as ASCII heatmap."""
    lines = ["# Coupling Heat Map", ""]
    lines.append("```")

    header = "           " + "".join(f"{i:3}" for i in range(len(classes)))
    lines.append(header)
    lines.append("           " + "---" * len(classes))

    for i, cls1 in enumerate(classes):
        row = f"{i:2} {cls1[:7]:<7} "
        for cls2 in classes:
            if cls1 == cls2:
                row += "  ."
            else:
                strength = matrix.get(cls1, {}).get(cls2, 0)
                if strength == 0:
                    row += "  ."
                elif strength <= 3:
                    row += "  o"  # Low
                elif strength <= 7:
                    row += "  O"  # Medium
                else:
                    row += "  #"  # High
        lines.append(row)

    lines.append("```")
    lines.append("")
    lines.append("**Legend**: . = none, o = low (1-3), O = medium (4-7), # = high (8+)")
    lines.append("")
    lines.append("## Class Index")

    for i, cls in enumerate(classes):
        lines.append(f"{i:2} . {cls}")

    return "\n".join(lines)

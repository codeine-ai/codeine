"""
sequence_diagram - Generate Mermaid sequence diagram.

Shows method calls between classes as sequence interactions.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("sequence_diagram")
@param("classes", list, required=True, description="List of class names to include")
@param("entry_point", str, required=False, default=None, description="Entry point method name")
@param("max_depth", int, default=10, description="Maximum call depth to traverse")
@param("format", str, default="mermaid", description="Output format: json, mermaid")
def sequence_diagram() -> Pipeline:
    """
    Generate sequence diagram showing method calls.

    Returns:
        diagram: Mermaid sequence diagram
        sequences: List of interaction data
        total_interactions: Number of method interactions
    """
    return (
        reql('''
            SELECT ?caller ?callerName ?callee ?calleeName ?callerClassName ?calleeClassName
            WHERE {
                ?caller type {Method} .
                ?caller name ?callerName .
                ?caller calls ?callee .
                ?callee type {Method} .
                ?callee name ?calleeName .
                ?caller definedIn ?callerClass .
                ?callee definedIn ?calleeClass .
                ?callerClass name ?callerClassName .
                ?calleeClass name ?calleeClassName
            }
            ORDER BY ?callerClassName ?callerName
        ''')
        .filter(_filter_by_classes)
        .filter(_filter_by_entry_point)
        .select("callerClassName", "callerName", "calleeClassName", "calleeName")
        .map(lambda r: {
            **r,
            'caller_class': r['callerClassName'],
            'caller_method': r['callerName'],
            'callee_class': r['calleeClassName'],
            'callee_method': r['calleeName']
        })
        .tap(_collect_for_render)
        .render(format="{format}", renderer=_render_sequence)
        .emit("diagram")
    )


def _filter_by_classes(row, ctx=None):
    """Filter to include rows involving specified classes."""
    if ctx is None:
        return True
    classes = ctx.params.get('classes', [])
    if not classes:
        return True
    # Handle both raw REQL output (?key) and post-select (key)
    caller = row.get("callerClassName") or row.get("?callerClassName")
    callee = row.get("calleeClassName") or row.get("?calleeClassName")
    return caller in classes or callee in classes


def _filter_by_entry_point(row, ctx=None):
    """Filter by entry point if specified."""
    if ctx is None:
        return True
    entry_point = ctx.params.get('entry_point')
    if not entry_point:
        return True
    # Handle both raw REQL output (?key) and post-select (key)
    caller_name = row.get("callerName") or row.get("?callerName")
    return caller_name == entry_point


def _collect_for_render(data, ctx=None):
    """Collect classes list for rendering."""
    classes = []
    if ctx is not None:
        classes = ctx.params.get('classes', [])
    return {'sequences': data, 'classes': classes}


def _render_sequence(data, format):
    """Render sequence diagram in requested format."""
    # Extract sequences and classes from data
    if isinstance(data, dict):
        if '_tap_result' in data:
            tap_data = data['_tap_result']
            seq_list = tap_data.get('sequences', [])
            classes = tap_data.get('classes', [])
        elif 'items' in data:
            seq_list = list(data['items'])
            classes = []
        else:
            seq_list = data.get('sequences', [])
            classes = data.get('classes', [])
    elif isinstance(data, list):
        seq_list = data
        classes = []
    else:
        seq_list = [data]
        classes = []

    if format == "json":
        return {"sequences": seq_list, "total_interactions": len(seq_list)}

    lines = ["```mermaid", "sequenceDiagram", ""]

    # Declare participants
    if classes:
        class_list = sorted(classes)
    else:
        class_list = sorted(set(
            [s.get('caller_class') for s in seq_list if s.get('caller_class')] +
            [s.get('callee_class') for s in seq_list if s.get('callee_class')]
        ))

    for cls in class_list:
        if cls:
            lines.append(f"    participant {cls}")

    lines.append("")

    # Render interactions
    for seq in seq_list:
        caller = seq.get('caller_class')
        callee = seq.get('callee_class')
        method = seq.get('callee_method')

        if not all([caller, callee, method]):
            continue

        if caller == callee:
            lines.append(f"    {caller}->>{caller}: {method}()")
        else:
            lines.append(f"    {caller}->>+{callee}: {method}()")
            lines.append(f"    {callee}-->>-{caller}: return")

    lines.append("```")
    return "\n".join(lines)

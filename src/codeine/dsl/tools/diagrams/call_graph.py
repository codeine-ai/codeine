"""
call_graph - Generate function/method call graph.

Shows call relationships centered on a focus function.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("call_graph")
@param("focus_function", str, required=True, description="Function/method name to focus on")
@param("direction", str, default="both", description="Traversal: upstream, downstream, both")
@param("max_depth", int, default=3, description="Maximum depth to traverse")
@param("format", str, default="mermaid", description="Output format: json, markdown, mermaid")
def call_graph() -> Pipeline:
    """
    Generate call graph centered on a function.

    Returns:
        diagram: Formatted call graph visualization
        focus_function: The central function
        nodes: Functions in the graph
        edges: Call relationships
    """
    return (
        reql('''
            SELECT ?callerName ?calleeName
            WHERE {
                ?caller calls ?callee .
                ?caller name ?callerName .
                ?callee name ?calleeName
            }
            ORDER BY ?callerName ?calleeName
        ''')
        .select("callerName", "calleeName")
        .map(lambda r: {"from": r["callerName"], "to": r["calleeName"]})
        .tap(_build_call_graph)
        .render(format="{format}", renderer=_render_call_graph)
        .emit("diagram")
    )


def _build_call_graph(edges, ctx=None):
    """Build filtered call graph from focus function."""
    focus_function = "unknown"
    direction = "both"
    max_depth = 3

    if ctx is not None:
        focus_function = ctx.params.get('focus_function', 'unknown')
        direction = ctx.params.get('direction', 'both')
        max_depth = ctx.params.get('max_depth', 3)

    call_graph = {}
    reverse_graph = {}

    for edge in edges:
        caller = edge.get('from')
        callee = edge.get('to')

        if caller not in call_graph:
            call_graph[caller] = []
        call_graph[caller].append(callee)

        if callee not in reverse_graph:
            reverse_graph[callee] = []
        reverse_graph[callee].append(caller)

    nodes = set()
    result_edges = []

    def traverse_downstream(func, depth):
        if depth > max_depth or func in nodes:
            return
        nodes.add(func)
        for callee in call_graph.get(func, []):
            result_edges.append({"from": func, "to": callee, "type": "calls"})
            traverse_downstream(callee, depth + 1)

    def traverse_upstream(func, depth):
        if depth > max_depth or func in nodes:
            return
        nodes.add(func)
        for caller in reverse_graph.get(func, []):
            result_edges.append({"from": caller, "to": func, "type": "calls"})
            traverse_upstream(caller, depth + 1)

    nodes.add(focus_function)

    if direction in ["downstream", "both"]:
        traverse_downstream(focus_function, 0)

    if direction in ["upstream", "both"]:
        traverse_upstream(focus_function, 0)

    return {
        "nodes": list(nodes),
        "edges": result_edges,
        "focus_function": focus_function,
        "direction": direction
    }


def _render_call_graph(data, format):
    """Render call graph in requested format."""
    # Extract from tap result
    if isinstance(data, dict) and '_tap_result' in data:
        data = data['_tap_result']

    if isinstance(data, dict) and 'nodes' in data:
        nodes = data['nodes']
        edges = data['edges']
        focus_function = data.get('focus_function', 'unknown')
        direction = data.get('direction', 'both')
    else:
        # Fallback: extract from raw data
        edges = list(data) if isinstance(data, (list, tuple)) else []
        nodes = set()
        for e in edges:
            nodes.add(e.get('from'))
            nodes.add(e.get('to'))
        nodes = list(nodes)
        focus_function = 'unknown'
        direction = 'both'

    if format == "json":
        return {
            "focus_function": focus_function,
            "nodes": nodes,
            "edges": edges,
            "direction": direction
        }

    if format == "mermaid":
        return _render_mermaid(nodes, edges, focus_function)

    # Markdown format
    lines = [f"# Call Graph: `{focus_function}`", ""]
    lines.append(f"**Direction**: {direction}")
    lines.append(f"**Total Functions**: {len(nodes)}")
    lines.append("")

    # Group edges by caller
    callers = {}
    for edge in edges:
        caller = edge['from']
        callee = edge['to']
        if caller not in callers:
            callers[caller] = []
        callers[caller].append(callee)

    lines.append("## Call Relationships")
    lines.append("")

    for caller in sorted(callers.keys()):
        marker = "**[FOCUS]** " if caller == focus_function else ""
        lines.append(f"- {marker}`{caller}`")
        for callee in sorted(callers[caller]):
            lines.append(f"  - -> `{callee}`")

    return "\n".join(lines)


def _render_mermaid(nodes, edges, focus_function):
    """Render as Mermaid flowchart."""
    lines = ["```mermaid", "flowchart TB"]

    # Declare nodes
    for node in sorted(nodes):
        node_id = node.replace('.', '_').replace('-', '_')
        if node == focus_function:
            # Highlight focus function
            lines.append(f'    {node_id}["{node}"]')
            lines.append(f'    style {node_id} fill:#ff0,stroke:#000,stroke-width:2px')
        else:
            lines.append(f'    {node_id}["{node}"]')

    lines.append("")

    # Render edges
    for edge in edges:
        from_node = edge['from'].replace('.', '_').replace('-', '_')
        to_node = edge['to'].replace('.', '_').replace('-', '_')
        lines.append(f'    {from_node} --> {to_node}')

    lines.append("```")
    return "\n".join(lines)

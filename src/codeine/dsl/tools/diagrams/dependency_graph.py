"""
dependency_graph - Generate module dependency graph.

Shows module import relationships with optional circular dependency detection.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("dependency_graph")
@param("show_external", bool, default=False, description="Include external/stdlib imports")
@param("module_filter", str, required=False, default=None, description="Filter modules by prefix")
@param("highlight_circular", bool, default=True, description="Highlight circular dependencies")
@param("format", str, default="mermaid", description="Output format: json, markdown, mermaid")
@param("limit", int, default=100, description="Maximum dependencies to return")
def dependency_graph() -> Pipeline:
    """
    Generate module dependency graph.

    Returns:
        diagram: Formatted dependency visualization
        dependencies: List of dependency edges
        circular_dependencies: Detected circular imports
        summary: Dependency statistics
    """
    return (
        reql('''
            SELECT ?moduleName ?imported
            WHERE {
                ?module type {Module} .
                ?module name ?moduleName .
                ?import type {Import} .
                ?import inModule ?module .
                ?import imports ?imported
            }
            ORDER BY ?moduleName ?imported
        ''')
        .select("moduleName", "imported")
        .filter(_filter_dependency)
        .map(lambda r: {"from": r["moduleName"], "to": r["imported"]})
        .tap(_detect_circular)
        .render(format="{format}", renderer=_render_dependency_graph)
        .emit("diagram")
    )


def _filter_dependency(row, ctx=None):
    """Filter dependencies based on options."""
    show_external = False
    module_filter = None

    if ctx is not None:
        show_external = ctx.params.get('show_external', False)
        module_filter = ctx.params.get('module_filter')

    # Handle both raw REQL output (?key) and post-select (key)
    imported = row.get('imported') or row.get('?imported') or ''
    module_name = row.get('moduleName') or row.get('?moduleName') or ''

    # Filter external
    if not show_external:
        if imported.startswith('__builtin__') or '.' not in imported:
            return False

    # Filter by module prefix
    if module_filter:
        if not (module_name.startswith(module_filter) or imported.startswith(module_filter)):
            return False

    return True


def _detect_circular(dependencies, ctx=None):
    """Detect circular dependencies using DFS."""
    highlight_circular = True
    if ctx is not None:
        highlight_circular = ctx.params.get('highlight_circular', True)

    if not highlight_circular:
        return {"dependencies": dependencies, "circular": []}

    graph = {}
    for dep in dependencies:
        frm = dep.get('from')
        to = dep.get('to')
        if frm not in graph:
            graph[frm] = []
        graph[frm].append(to)

    cycles = []
    visited = set()
    rec_stack = set()

    def dfs(node, path):
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path.copy())
            elif neighbor in rec_stack:
                cycle_start = path.index(neighbor) if neighbor in path else -1
                if cycle_start >= 0:
                    cycle = path[cycle_start:] + [neighbor]
                    if cycle not in cycles:
                        cycles.append(cycle)

        rec_stack.discard(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return {"dependencies": dependencies, "circular": cycles}


def _render_dependency_graph(data, format):
    """Render dependency graph in requested format."""
    # Extract from tap result
    if isinstance(data, dict) and '_tap_result' in data:
        data = data['_tap_result']

    if isinstance(data, dict):
        dep_list = data.get('dependencies', [])
        circular = data.get('circular', [])
    elif isinstance(data, list):
        dep_list = data
        circular = []
    else:
        dep_list = [data]
        circular = []

    if format == "json":
        return {
            "dependencies": dep_list,
            "circular_dependencies": circular,
            "total": len(dep_list)
        }

    if format == "mermaid":
        return _render_mermaid(dep_list, circular)

    # Markdown format
    lines = ["# Module Dependency Graph", ""]

    if circular:
        lines.append("## Circular Dependencies Detected")
        lines.append("")
        for i, cycle in enumerate(circular, 1):
            lines.append(f"{i} . {' -> '.join(cycle)}")
        lines.append("")

    # Group by source module
    packages = {}
    for dep in dep_list:
        from_pkg = dep['from'].split('.')[0] if '.' in dep['from'] else dep['from']
        if from_pkg not in packages:
            packages[from_pkg] = []
        packages[from_pkg].append(dep)

    lines.append("## Dependencies by Package")
    lines.append("")

    for pkg in sorted(packages.keys()):
        lines.append(f"### {pkg}")
        lines.append("")
        for dep in sorted(packages[pkg], key=lambda x: x['from']):
            is_circular = any(dep['from'] in c and dep['to'] in c for c in circular)
            marker = "**[CIRCULAR]** " if is_circular else ""
            lines.append(f"- {marker}`{dep['from']}` -> `{dep['to']}`")
        lines.append("")

    return "\n".join(lines)


def _render_mermaid(dependencies, circular):
    """Render as Mermaid flowchart."""
    lines = ["```mermaid", "flowchart LR"]

    circular_edges = set()
    for cycle in circular:
        for i in range(len(cycle) - 1):
            circular_edges.add((cycle[i], cycle[i + 1]))

    # Collect unique nodes
    nodes = set()
    for dep in dependencies:
        nodes.add(dep['from'])
        nodes.add(dep['to'])

    # Declare nodes with sanitized IDs
    for node in sorted(nodes):
        node_id = node.replace('.', '_').replace('-', '_')
        lines.append(f'    {node_id}["{node}"]')

    lines.append("")

    # Render edges
    for dep in dependencies:
        from_node = dep['from'].replace('.', '_').replace('-', '_')
        to_node = dep['to'].replace('.', '_').replace('-', '_')

        if (dep['from'], dep['to']) in circular_edges:
            # Red styling for circular deps
            lines.append(f'    {from_node} --> {to_node}')
            lines.append(f'    style {from_node} stroke:#f00,stroke-width:2px')
            lines.append(f'    style {to_node} stroke:#f00,stroke-width:2px')
        else:
            lines.append(f'    {from_node} --> {to_node}')

    lines.append("```")
    return "\n".join(lines)

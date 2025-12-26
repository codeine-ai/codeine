"""
class_hierarchy - Generate class inheritance hierarchy diagram.

Shows class inheritance trees in markdown or JSON format.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("class_hierarchy")
@param("root_class", str, required=False, default=None, description="Root class to start from")
@param("format", str, default="markdown", description="Output format: json, markdown")
def class_hierarchy() -> Pipeline:
    """
    Generate class inheritance hierarchy.

    Returns:
        diagram: Formatted hierarchy visualization
        hierarchy: Tree structure data
        total_classes: Number of classes in hierarchy
    """
    return (
        reql('''
            SELECT ?c ?className ?base ?baseName
            WHERE {
                ?c type {Class} .
                ?c name ?className .
                OPTIONAL {
                    ?c inheritsFrom ?base .
                    ?base name ?baseName
                }
            }
            ORDER BY ?className
        ''')
        .select("className", "baseName", class_iri="c", base_iri="base")
        .group_by(
            key=lambda r: "hierarchy",
            aggregate=_build_hierarchy  # Now accepts (rows, ctx)
        )
        .render(format="{format}", renderer=_render_hierarchy)
        .emit("diagram")
    )


def _build_hierarchy(rows, ctx=None):
    """Build hierarchy tree from query results."""
    # Extract root_class from context params
    root_class = None
    if ctx is not None:
        root_class = ctx.params.get('root_class')

    classes = {}
    all_classes = set()

    for row in rows:
        class_name = row.get('className')
        base_name = row.get('baseName')

        if class_name:
            all_classes.add(class_name)
            if class_name not in classes:
                classes[class_name] = {
                    'name': class_name,
                    'bases': [],
                    'children': []
                }

            if base_name:
                classes[class_name]['bases'].append(base_name)
                all_classes.add(base_name)

                if base_name not in classes:
                    classes[base_name] = {
                        'name': base_name,
                        'bases': [],
                        'children': []
                    }
                classes[base_name]['children'].append(class_name)

    # Find root classes
    if root_class and root_class != "None":
        roots = [classes[root_class]] if root_class in classes else []
    else:
        roots = [c for c in classes.values() if not c['bases']]

    return {
        'roots': roots,
        'all_classes': sorted(list(all_classes)),
        'class_details': classes
    }


def _render_hierarchy(data, format):
    """Render hierarchy in requested format."""
    # Extract hierarchy from GroupByStep's {"items": {"hierarchy": ...}} structure
    if isinstance(data, dict) and "items" in data:
        hierarchy = data["items"].get("hierarchy", data)
    else:
        hierarchy = data

    if format == "json":
        return {"hierarchy": hierarchy, "total_classes": len(hierarchy.get('all_classes', []))}

    lines = ["# Class Hierarchy\n"]

    def render_tree(class_info, class_details, indent=0):
        prefix = "  " * indent + ("- " if indent > 0 else "")
        lines.append(f"{prefix}**{class_info['name']}**")

        for child_name in sorted(class_info.get('children', [])):
            if child_name in class_details:
                render_tree(class_details[child_name], class_details, indent + 1)

    for root in hierarchy.get('roots', []):
        render_tree(root, hierarchy.get('class_details', {}))

    lines.append(f"\n**Total classes:** {len(hierarchy.get('all_classes', []))}")

    return "\n".join(lines)

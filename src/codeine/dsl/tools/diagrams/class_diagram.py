"""
class_diagram - Generate Mermaid class diagram.

Shows class details with attributes, methods, and inheritance.
"""

from codeine.dsl import diagram, param, reql, Pipeline


@diagram("class_diagram")
@param("classes", list, required=True, description="List of class names to include")
@param("include_methods", bool, default=True, description="Include methods")
@param("include_attributes", bool, default=True, description="Include attributes")
@param("format", str, default="mermaid", description="Output format: json, mermaid")
def class_diagram() -> Pipeline:
    """
    Generate class diagram with attributes and methods.

    Returns:
        diagram: Mermaid class diagram
        classes: List of class data
        total_classes: Number of classes included
    """
    return (
        reql('''
            SELECT ?c ?className ?base ?baseName ?m ?methodName ?a ?attrName
            WHERE {
                ?c type {Class} .
                ?c name ?className .
                OPTIONAL { ?c inheritsFrom ?base . ?base name ?baseName }
                OPTIONAL { ?m type {Method} . ?m definedIn ?c . ?m name ?methodName }
                OPTIONAL { ?a type {Attribute} . ?a definedIn ?c . ?a name ?attrName }
            }
            ORDER BY ?className ?methodName ?attrName
        ''')
        .filter(_filter_classes)  # Now accepts (row, ctx)
        .select("className", "baseName", "methodName", "attrName")
        .group_by(
            key=lambda r: r.get("className"),
            aggregate=_aggregate_class  # Now accepts (rows, ctx)
        )
        .render(format="{format}", renderer=_render_class_diagram)
        .emit("diagram")
    )


def _filter_classes(row, ctx=None):
    """Filter to only include specified classes."""
    if ctx is None:
        return True
    classes = ctx.params.get('classes', [])
    if not classes:
        return True
    # Handle both raw REQL output (?className) and post-select (className)
    class_name = row.get("className") or row.get("?className")
    return class_name in classes


def _aggregate_class(rows, ctx=None):
    """Aggregate class data from rows."""
    include_methods = True
    include_attributes = True
    if ctx is not None:
        include_methods = ctx.params.get('include_methods', True)
        include_attributes = ctx.params.get('include_attributes', True)

    class_info = {
        'name': None,
        'bases': set(),
        'methods': set(),
        'attributes': set()
    }

    for row in rows:
        if not class_info['name']:
            class_info['name'] = row.get('className')

        if row.get('baseName'):
            class_info['bases'].add(row['baseName'])

        if include_methods and row.get('methodName'):
            class_info['methods'].add(row['methodName'])

        if include_attributes and row.get('attrName'):
            class_info['attributes'].add(row['attrName'])

    return {
        'name': class_info['name'],
        'bases': sorted(list(class_info['bases'])),
        'methods': sorted(list(class_info['methods'])),
        'attributes': sorted(list(class_info['attributes']))
    }


def _render_class_diagram(class_data, format):
    """Render class diagram in requested format."""
    if isinstance(class_data, dict) and 'items' in class_data:
        classes = list(class_data['items'].values())
    elif isinstance(class_data, list):
        classes = class_data
    else:
        classes = [class_data]

    if format == "json":
        return {"classes": classes, "total_classes": len(classes)}

    lines = ["```mermaid", "classDiagram", ""]

    # Render inheritance first
    for cls in classes:
        for base in cls.get('bases', []):
            lines.append(f"    {base} <|-- {cls['name']}")

    if any(cls.get('bases') for cls in classes):
        lines.append("")

    # Render each class
    for cls in classes:
        name = cls['name']
        attrs = cls.get('attributes', [])
        methods = cls.get('methods', [])

        if attrs or methods:
            lines.append(f"    class {name} {{")

            for attr in attrs:
                visibility = '-' if attr.startswith('_') else '+'
                lines.append(f"        {visibility}{attr}")

            for method in methods:
                if method.startswith('__') and not method.endswith('__'):
                    visibility = '-'
                elif method.startswith('_'):
                    visibility = '-'
                else:
                    visibility = '+'
                lines.append(f"        {visibility}{method}()")

            lines.append("    }")
        else:
            lines.append(f"    class {name}")

        lines.append("")

    lines.append("```")
    return "\n".join(lines)

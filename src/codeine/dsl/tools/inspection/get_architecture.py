"""
get_architecture - Generate high-level architectural overview.

Returns a comprehensive view of the codebase architecture.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_architecture")
@param("format", str, default="json", description="Output format: json, markdown, or mermaid")
def get_architecture() -> Pipeline:
    """
    Generate high-level architectural overview.

    Returns:
        overview: High-level architecture summary
        layers: Architectural layers identified
        components: Major components and their relationships
    """
    return (
        reql('''
            SELECT ?file (COUNT(?class) AS ?class_count) (COUNT(?func) AS ?function_count) (COUNT(?import) AS ?import_count)
            WHERE {
                ?m type {Module} .
                ?m inFile ?file .
                OPTIONAL { ?class type {Class} . ?class inFile ?file }
                OPTIONAL { ?func type {Function} . ?func inFile ?file }
                OPTIONAL { ?m imports ?import }
            }
            GROUP BY ?file
            ORDER BY ?file
        ''')
        .select("file", "class_count", "function_count", "import_count")
        .emit("architecture")
    )

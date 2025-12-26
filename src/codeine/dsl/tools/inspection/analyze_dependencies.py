"""
analyze_dependencies - Analyze module dependency graph.

Returns the complete dependency graph including circular dependencies.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("analyze_dependencies")
@param("limit", int, default=100, description="Maximum results to return")
def analyze_dependencies() -> Pipeline:
    """
    Analyze module dependency graph.

    Returns:
        dependencies: List of module dependencies
        circular_dependencies: List of circular dependency chains
        summary: Dependency statistics
    """
    return (
        reql('''
            SELECT ?m ?module_name ?imports_name ?file
            WHERE {
                ?m type {Module} .
                ?m name ?module_name .
                ?m inFile ?file .
                OPTIONAL {
                    ?m imports ?imported .
                    ?imported name ?imports_name
                }
            }
            ORDER BY ?module_name
        ''')
        .select("module_name", "imports_name", "file", qualified_name="m")
        .emit("dependencies")
    )

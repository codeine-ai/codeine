"""
get_type_hints - Extract all type annotations from parameters and returns.

Returns type annotation coverage and details for the codebase.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_type_hints")
@param("limit", int, default=100, description="Maximum results to return")
def get_type_hints() -> Pipeline:
    """
    Extract all type annotations from parameters and returns.

    Returns:
        type_hints: List of type annotations found
        coverage_stats: Statistics on type annotation coverage
    """
    return (
        reql('''
            SELECT ?e ?entity_name ?entity_type ?param_name ?param_type ?return_type ?file ?line
            WHERE {
                { ?e type {Method} } UNION { ?e type {Function} }
                ?e name ?entity_name .
                ?e inFile ?file .
                ?e atLine ?line .
                OPTIONAL { ?e returnType ?return_type }
                OPTIONAL {
                    ?e hasParameter ?p .
                    ?p name ?param_name .
                    ?p typeAnnotation ?param_type
                }
                
                
            }
            ORDER BY ?file ?line
        ''')
        .select("entity_name", "entity_type", "param_name", "param_type", "return_type", "file", "line")
        .emit("type_hints")
    )

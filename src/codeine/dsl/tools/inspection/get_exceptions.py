"""
get_exceptions - Get exception class hierarchy.

Returns all exception classes and their inheritance relationships.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_exceptions")
@param("limit", int, default=100, description="Maximum results to return")
def get_exceptions() -> Pipeline:
    """
    Get exception class hierarchy.

    Returns:
        exceptions: List of exception classes
        hierarchy: Exception inheritance hierarchy
        custom_exceptions: List of custom exception classes
    """
    return (
        reql('''
            SELECT ?e ?name ?parent_name ?file ?line ?is_custom
            WHERE {
                ?e type {Class} .
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                ?e inheritsFrom ?base .
                ?base name "Exception".
                OPTIONAL {
                    ?e inheritsFrom ?parent .
                    ?parent name ?parent_name
                }
                            }
            ORDER BY ?name
        ''')
        .select("name", "parent_name", "file", "line", "is_custom", qualified_name="e")
        .emit("exceptions")
    )

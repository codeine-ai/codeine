"""
get_docstring - Get the docstring of a class, method, or function.

Returns the docstring and entity type for the specified target.

Reference: d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:777-827
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_docstring")
@param("target", str, required=True, description="Name of class, method, or function")
def get_docstring() -> Pipeline:
    """
    Get the docstring of a class, method, or function.

    Returns:
        docstring: The docstring text (or None if not present)
        entity_type: Type of entity (class, method, function)
        name: Entity name
        qualified_name: Fully qualified name
        file: File path
        line: Line number
    """
    return (
        reql('''
            SELECT ?e ?name ?docstring ?file ?line ?type
            WHERE {
                { ?e type {Class} } UNION { ?e type {Method} } UNION { ?e type {Function} }
                ?e type ?type .
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                OPTIONAL { ?e docstring ?docstring }
                FILTER ( CONTAINS(?name, "{target}") || CONTAINS(?e, "{target}") )
            }
        ''')
        .select("name", "docstring", "file", "line", "type", qualified_name="e")
        .emit("result")
    )

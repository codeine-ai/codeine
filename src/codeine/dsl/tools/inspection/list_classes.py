"""
list_classes - List all classes in the codebase.

Returns a list of all classes, optionally filtered by module.

Reference: d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:130-239
"""

from codeine.dsl import query, param, reql, Pipeline


@query("list_classes")
@param("module", str, required=False, default="", description="Filter by module/file name")
@param("limit", int, default=100, description="Maximum results to return")
@param("offset", int, default=0, description="Number of results to skip")
def list_classes() -> Pipeline:
    """
    List all classes in the codebase or a specific module.

    Returns:
        classes: List of class info dicts with name, qualified_name, file, line, method_count
        count: Number of classes returned
        has_more: Whether more results exist
    """
    return (
        reql('''
            SELECT ?c ?name ?qualifiedName ?file ?line (COUNT(?method) AS ?methodCount)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c qualifiedName ?qualifiedName .
                ?c inFile ?file .
                ?c atLine ?line .
                OPTIONAL { ?method type {Method} . ?method definedIn ?c }
                FILTER ( "{module}" = "" || CONTAINS(?file, "{module}") )
            }
            GROUP BY ?c ?name ?qualifiedName ?file ?line
            ORDER BY ?name
        ''')
        .select("name", "qualifiedName", "file", "line", "methodCount", qualified_name="c")
        .emit("classes")
    )

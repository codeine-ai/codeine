"""
list_functions - List all top-level functions in the codebase.

Returns a list of all module-level functions (not methods).

Reference: d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:854-914
"""

from codeine.dsl import query, param, reql, Pipeline


@query("list_functions")
@param("module", str, required=False, default="", description="Filter by module/file name")
@param("limit", int, default=100, description="Maximum results to return")
@param("offset", int, default=0, description="Number of results to skip")
def list_functions() -> Pipeline:
    """
    List all top-level functions in the codebase or a specific module.

    Returns:
        functions: List of function info dicts with name, qualifiedName, file, line, returnType
        count: Number of functions returned
        has_more: Whether more results exist
    """
    return (
        reql('''
            SELECT ?f ?name ?qualifiedName ?file ?line ?returnType
            WHERE {
                ?f type {Function} .
                ?f name ?name .
                ?f qualifiedName ?qualifiedName .
                ?f inFile ?file .
                ?f atLine ?line .
                OPTIONAL { ?f returnType ?returnType }
                FILTER NOT EXISTS { ?f definedIn ?class }
                FILTER ( "{module}" = "" || CONTAINS(?file, "{module}") )
            }
            ORDER BY ?name
        ''')
        .select("name", "qualifiedName", "file", "line", "returnType", qualified_name="f")
        .emit("functions")
    )

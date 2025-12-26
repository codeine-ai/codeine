"""
list_modules - List all modules in the codebase.

Returns a list of all Python modules with their file paths.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("list_modules")
@param("limit", int, default=100, description="Maximum results to return")
@param("offset", int, default=0, description="Number of results to skip")
def list_modules() -> Pipeline:
    """
    List all modules in the codebase.

    Returns:
        modules: List of module info dicts with name, file, qualified_name
        count: Number of modules returned
        total_count: Total modules in codebase
    """
    return (
        reql('''
            SELECT ?m ?name ?file
            WHERE {
                ?m type {Module} .
                ?m name ?name .
                ?m inFile ?file
            }
        ''')
        .select("name", "file", qualified_name="m")
        .order_by("file")
        .emit("modules")
    )

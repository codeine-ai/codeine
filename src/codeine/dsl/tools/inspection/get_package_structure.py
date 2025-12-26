"""
get_package_structure - Get package/module directory structure.

Returns the hierarchical structure of modules in the codebase.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_package_structure")
@param("limit", int, default=100, description="Maximum results to return")
@param("offset", int, default=0, description="Number of results to skip")
def get_package_structure() -> Pipeline:
    """
    Get package/module directory structure.

    Returns:
        modules: List of module info with file paths
        by_directory: Modules grouped by directory
        module_count: Total number of modules
    """
    return (
        reql('''
            SELECT ?m ?name ?file
            WHERE {
                ?m type {Module} .
                ?m name ?name .
                ?m inFile ?file
            }
            ORDER BY ?file
        ''')
        .select("name", "file", qualified_name="m")
        .emit("modules")
    )

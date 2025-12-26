"""
get_imports - Get complete module import dependency graph.

Returns all imports in the codebase with their sources and targets.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_imports")
@param("limit", int, default=100, description="Maximum results to return")
def get_imports() -> Pipeline:
    """
    Get complete module import dependency graph.

    Returns:
        imports: List of import statements with source module, imported name, alias
        import_graph: Graph structure of module dependencies
        external_deps: List of external package imports
    """
    return (
        reql('''
            SELECT ?i ?module_name ?imported_name ?alias ?file ?line ?is_from
            WHERE {
                ?i type {Import} .
                ?i inFile ?file .
                ?i atLine ?line .
                ?i name ?imported_name .
                OPTIONAL { ?i alias ?alias }
                OPTIONAL { ?i fromModule ?from . ?from name ?module_name }
                OPTIONAL { ?i isFromImport ?is_from }
            }
            ORDER BY ?file ?line
        ''')
        .select("module_name", "imported_name", "alias", "file", "line", "is_from", qualified_name="i")
        .emit("imports")
    )

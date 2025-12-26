"""
get_api_docs - Extract all API documentation from docstrings.

Returns comprehensive documentation coverage for the codebase.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_api_docs")
@param("limit", int, default=100, description="Maximum results to return")
def get_api_docs() -> Pipeline:
    """
    Extract all API documentation from docstrings.

    Returns:
        documentation: Dict of entities with their docstrings
        coverage_stats: Statistics on documentation coverage
    """
    return (
        reql('''
            SELECT ?e ?name ?entity_type ?docstring ?file ?line
            WHERE {
                { ?e type {Class}  }
                UNION
                { ?e type {Method}  }
                UNION
                { ?e type {Function}  }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                OPTIONAL { ?e docstring ?docstring }
            }
            ORDER BY ?file ?line
        ''')
        .select("name", "entity_type", "docstring", "file", "line", qualified_name="e")
        .emit("documentation")
    )

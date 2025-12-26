"""
silent_exception_swallowing - Detect empty except blocks.

Identifies except blocks that silently swallow exceptions with
empty bodies or just 'pass' statements.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("silent_exception_swallowing", category="exception_handling", severity="critical")
@param("limit", int, default=100, description="Maximum results to return")
def silent_exception_swallowing() -> Pipeline:
    """
    Detect empty except blocks that silently swallow exceptions.

    Returns:
        findings: List of silent exception handlers
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?h ?exception_type ?func_name ?file ?line ?body_size
            WHERE {
                ?h type {CatchClause} .
                ?h inFile ?file .
                ?h atLine ?line .
                ?h bodySize ?body_size .
                OPTIONAL { ?h exceptionType ?exception_type }
                OPTIONAL { ?h inFunction ?f . ?f name ?func_name                 FILTER ( ?body_size <= 1 )
            }
            }
            ORDER BY ?file ?line
        ''')
        .select("exception_type", "func_name", "file", "line", "body_size")
        .map(lambda r: {
            **r,
            "issue": "silent_exception_swallowing",
            "message": f"Empty except block for '{r.get('exception_type', 'Exception')}' in '{r.get('func_name', 'unknown')}'",
            "suggestion": "Log the exception or handle it appropriately; avoid silently swallowing"
        })
        .emit("findings")
    )

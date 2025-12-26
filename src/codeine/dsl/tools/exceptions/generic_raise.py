"""
generic_exception_raising - Detect raising generic Exception.

Identifies code that raises generic Exception instead of
specific exception types.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("generic_exception_raising", category="exception_handling", severity="medium")
@param("limit", int, default=100, description="Maximum results to return")
def generic_exception_raising() -> Pipeline:
    """
    Detect raising generic Exception types.

    Returns:
        findings: List of generic exception raises
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?r ?exception_type ?func_name ?file ?line
            WHERE {
                ?r type {ThrowStatement} .
                ?r inFile ?file .
                ?r atLine ?line .
                ?r exceptionType ?exception_type .
                OPTIONAL { ?r inFunction ?f . ?f name ?func_name                 FILTER ( ?exception_type = "Exception" )
            }
            }
            ORDER BY ?file ?line
        ''')
        .select("exception_type", "func_name", "file", "line")
        .map(lambda r: {
            **r,
            "issue": "generic_exception_raising",
            "message": f"Raising generic 'Exception' in '{r.get('func_name', 'unknown')}'",
            "suggestion": "Create and raise a specific exception type"
        })
        .emit("findings")
    )

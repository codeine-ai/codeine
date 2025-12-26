"""
error_codes_over_exceptions - Detect functions returning error codes.

Identifies functions that return error codes or status tuples
instead of raising exceptions.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("error_codes_over_exceptions", category="exception_handling", severity="medium")
@param("limit", int, default=100, description="Maximum results to return")
def error_codes_over_exceptions() -> Pipeline:
    """
    Detect functions returning error codes instead of raising exceptions.

    Returns:
        findings: List of error code patterns
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?f ?name ?file ?line ?return_pattern
            WHERE {
                { ?f type {Function} } UNION { ?f type {Method} }
                ?f name ?name .
                ?f inFile ?file .
                ?f atLine ?line .
                ?f returnsErrorCode true.
                OPTIONAL { ?f returnPattern ?return_pattern }
            }
            ORDER BY ?file ?line
        ''')
        .select("name", "file", "line", "return_pattern")
        .map(lambda r: {
            **r,
            "issue": "error_codes_over_exceptions",
            "message": f"Function '{r['name']}' returns error codes instead of raising exceptions",
            "suggestion": "Consider using exceptions for error handling"
        })
        .emit("findings")
    )

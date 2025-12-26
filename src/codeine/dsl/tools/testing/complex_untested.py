"""
complex_untested - Find complex code without tests.

Identifies long methods/functions that have no test coverage.
Uses line count as a proxy for complexity (longer = more complex).
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("complex_untested", category="test_coverage", severity="high")
@param("min_lines", int, default=30, description="Minimum lines to consider complex")
@param("limit", int, default=100, description="Maximum results to return")
def complex_untested() -> Pipeline:
    """
    Find complex code without test coverage.

    Uses line count as a proxy for complexity since cyclomatic
    complexity is not available from the parser.

    Returns:
        findings: List of complex untested code
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?class_name ?file ?line ?line_count
            WHERE {
                { ?e type {Method} } UNION { ?e type {Function} }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                ?e lineCount ?line_count .
                OPTIONAL { ?e definedIn ?c . ?c name ?class_name                     FILTER ( ?line_count >= {min_lines} )
                }
                FILTER ( !REGEX(?file, "test") )
                FILTER NOT EXISTS {
                    ?test calls ?e .
                    ?test inFile ?test_file .
                    FILTER ( REGEX(?test_file, "test") )
                }
            }
            ORDER BY DESC(?line_count)
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "line_count")
        .map(lambda r: {
            **r,
            "issue": "complex_untested",
            "message": f"Long {'method' if r.get('class_name') else 'function'} '{r['name']}' ({r['line_count']} lines) has no tests",
            "suggestion": "High-risk: add comprehensive tests for complex logic"
        })
        .emit("findings")
    )

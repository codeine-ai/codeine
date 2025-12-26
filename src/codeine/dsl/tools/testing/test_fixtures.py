"""
find_test_fixtures - Find pytest fixtures in the codebase.

Identifies all pytest fixtures and their usage.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_test_fixtures", category="test_coverage", severity="info")
@param("limit", int, default=100, description="Maximum results to return")
def find_test_fixtures() -> Pipeline:
    """
    Find pytest fixtures in the codebase.

    Returns:
        findings: List of pytest fixtures
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?f ?name ?file ?line ?scope ?usage_count
            WHERE {
                ?f type {Function} .
                ?f name ?name .
                ?f inFile ?file .
                ?f atLine ?line .
                ?f hasDecorator ?d .
                ?d name "fixture".
                OPTIONAL { ?f fixtureScope ?scope }
                OPTIONAL { ?f usageCount ?usage_count }
            }
            ORDER BY DESC(?usage_count)
        ''')
        .select("name", "file", "line", "scope", "usage_count")
        .emit("findings")
    )

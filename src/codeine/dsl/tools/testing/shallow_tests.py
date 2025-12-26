"""
shallow_tests - Find test classes with too few test methods.

Identifies test classes that may not have adequate coverage.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("shallow_tests", category="test_coverage", severity="low")
@param("min_tests", int, default=3, description="Minimum test methods expected")
@param("limit", int, default=100, description="Maximum results to return")
def shallow_tests() -> Pipeline:
    """
    Find test classes with too few test methods.

    Returns:
        findings: List of shallow test classes
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?test_method) AS ?test_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?test_method type {Method} .
                ?test_method definedIn ?c .
                ?test_method name ?method_name .
                FILTER ( STRSTARTS(?method_name, "test_") || STRSTARTS(?method_name, "test") )
                FILTER ( REGEX(?name, "^Test|Test$") )
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?test_count > 0 && ?test_count < {min_tests})
            ORDER BY ?test_count
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "test_count")
        .map(lambda r: {
            **r,
            "issue": "shallow_tests",
            "message": f"Test class '{r['name']}' has only {r.get('test_count', 0)} test methods",
            "suggestion": "Add more test methods for better coverage"
        })
        .emit("findings")
    )

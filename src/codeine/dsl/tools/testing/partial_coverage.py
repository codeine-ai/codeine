"""
partial_class_coverage - Find classes with partial test coverage.

Identifies classes where some but not all public methods are tested.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("partial_class_coverage", category="test_coverage", severity="low")
@param("limit", int, default=100, description="Maximum results to return")
def partial_class_coverage() -> Pipeline:
    """
    Find classes with partial test coverage.

    Returns:
        findings: List of partially tested classes
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?method) AS ?total_methods) (COUNT(?tested) AS ?tested_methods)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?method type {Method} .
                ?method definedIn ?c .
                ?method name ?method_name .
                FILTER ( !STRSTARTS(?method_name, "_") )
                OPTIONAL {
                    ?test calls ?method .
                    ?test inFile ?test_file .
                    FILTER ( REGEX(?test_file, "test_") )
                                    }
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?tested_methods > 0 && ?tested_methods < ?total_methods && ?total_methods > 2)
            ORDER BY ?tested_methods
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "tested_methods", "total_methods")
        .map(lambda r: {
            **r,
            "coverage_ratio": r.get('tested_methods', 0) / max(r.get('total_methods', 1), 1),
            "issue": "partial_coverage",
            "message": f"Class '{r['name']}' has {r.get('tested_methods', 0)}/{r.get('total_methods', 0)} methods tested",
            "suggestion": "Add tests for remaining public methods"
        })
        .emit("findings")
    )

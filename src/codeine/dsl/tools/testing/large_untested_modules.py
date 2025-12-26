"""
large_untested_modules - Find modules with many classes but few tests.

Identifies large modules that have inadequate test coverage.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("large_untested_modules", category="test_coverage", severity="medium")
@param("min_classes", int, default=5, description="Minimum classes for large module")
@param("limit", int, default=100, description="Maximum results to return")
def large_untested_modules() -> Pipeline:
    """
    Find modules with many classes but few tests.

    Returns:
        findings: List of large untested modules
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?file (COUNT(?class) AS ?class_count) (COUNT(?test) AS ?test_count)
            WHERE {
                ?class type {Class} .
                ?class inFile ?file .
                OPTIONAL {
                    ?test type {Class} .
                    ?test inFile ?test_file .
                    ?test name ?test_name .
                    FILTER ( REGEX(?test_name, "^Test|Test$") )
                    FILTER ( REGEX(?test_file, "test_") )
                    ?test_method definedIn ?test .
                    ?test_method calls ?method .
                    ?method definedIn ?class .
                FILTER ( !REGEX(?file, "test_") )
                                    }
            }
            GROUP BY ?file
            HAVING (?class_count >= {min_classes} && ?test_count < ?class_count / 2)
            ORDER BY DESC(?class_count)
            LIMIT {limit}
        ''')
        .select("file", "class_count", "test_count")
        .map(lambda r: {
            **r,
            "coverage_ratio": r.get('test_count', 0) / max(r.get('class_count', 1), 1),
            "issue": "large_untested_module",
            "message": f"Module '{r['file']}' has {r.get('class_count', 0)} classes but only {r.get('test_count', 0)} tests",
            "suggestion": "Add more tests to improve module coverage"
        })
        .emit("findings")
    )

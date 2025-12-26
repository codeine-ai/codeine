"""
extract_class - Suggest Extract Class refactoring opportunities.

Identifies classes that are doing too much and could be split
into multiple smaller, focused classes.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("extract_class", category="refactoring", severity="high")
@param("min_methods", int, default=15, description="Minimum methods to suggest extraction")
@param("limit", int, default=100, description="Maximum results to return")
def extract_class() -> Pipeline:
    """
    Suggest Extract Class refactoring opportunities.

    Returns:
        findings: List of classes that could benefit from extraction
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?method) AS ?method_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?method type {Method} .
                ?method definedIn ?c .
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?method_count >= {min_methods})
            ORDER BY DESC(?method_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "method_count", qualified_name="c")
        .map(lambda r: {
            **r,
            "refactoring": "extract_class",
            "message": f"Class '{r['name']}' ({r['method_count']} methods) may benefit from Extract Class",
            "suggestion": "Group related methods and attributes into separate classes"
        })
        .emit("findings")
    )

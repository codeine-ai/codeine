"""
god_class - Detect classes that do too much (God Class anti-pattern).

A God Class is a class that knows too much or does too much.
It typically has many methods, many attributes, and high coupling.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("god_class", category="design", severity="high")
@param("max_methods", int, default=15, description="Maximum methods threshold")
@param("limit", int, default=100, description="Maximum results to return")
def god_class() -> Pipeline:
    """
    Detect God Classes - classes that do too much.

    Returns:
        findings: List of potential God Classes with metrics
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
            HAVING (?method_count > {max_methods})
            ORDER BY DESC(?method_count)
        ''')
        .select("name", "file", "line", "method_count", qualified_name="c")
        .map(lambda r: {
            **r,
            "issue": "god_class",
            "message": f"Class '{r['name']}' appears to be a God Class with {r.get('method_count', 0)} methods",
            "suggestion": "Consider splitting responsibilities into smaller, focused classes"
        })
        .emit("findings")
    )

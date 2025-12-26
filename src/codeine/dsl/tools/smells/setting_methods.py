"""
setting_methods - Detect setter methods that could indicate immutability opportunities.

Excessive use of setters can lead to mutable objects with unpredictable state.
Consider making objects immutable with builder patterns or factory methods.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("setting_methods", category="code_smell", severity="low")
@param("min_setters", int, default=3, description="Minimum setters to flag class")
@param("limit", int, default=100, description="Maximum results to return")
def setting_methods() -> Pipeline:
    """
    Detect classes with many setter methods suggesting mutability issues.

    Returns:
        findings: List of classes with excessive setters
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?setter) AS ?setter_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?setter type {Method} .
                ?setter definedIn ?c .
                ?setter name ?setter_name .
                FILTER ( STRSTARTS(?setter_name, "set_") || STRSTARTS(?setter_name, "set") )
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?setter_count >= {min_setters})
            ORDER BY DESC(?setter_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "setter_count")
        .map(lambda r: {
            **r,
            "issue": "excessive_setters",
            "message": f"Class '{r['name']}' has {r['setter_count']} setter methods",
            "suggestion": "Consider making class immutable with constructor/builder initialization"
        })
        .emit("findings")
    )

"""
feature_envy - Detect methods that use other classes more than their own.

Feature Envy occurs when a method accesses data of another object
more than its own data. This suggests the method might belong elsewhere.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("feature_envy", category="design", severity="medium")
@param("min_external", int, default=3, description="Minimum external calls to flag")
@param("limit", int, default=100, description="Maximum results to return")
def feature_envy() -> Pipeline:
    """
    Detect methods with Feature Envy - methods that envy other classes.

    Returns:
        findings: List of methods with feature envy
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line (COUNT(?ext_call) AS ?external_calls)
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m definedIn ?c .
                ?c name ?class_name .
                ?m calls ?ext_call .
                ?ext_call definedIn ?ext_class .
                FILTER ( ?ext_class != ?c )
            }
            GROUP BY ?m ?name ?class_name ?file ?line
            HAVING (?external_calls >= {min_external})
            ORDER BY DESC(?external_calls)
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "external_calls", qualified_name="m")
        .map(lambda r: {
            **r,
            "issue": "feature_envy",
            "message": f"Method '{r['name']}' in '{r.get('class_name', 'unknown')}' makes {r['external_calls']} calls to other classes",
            "suggestion": "Consider moving this method to the class it envies"
        })
        .emit("findings")
    )

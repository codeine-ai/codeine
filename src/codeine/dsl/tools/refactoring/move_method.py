"""
move_method - Suggest Move Method refactoring opportunities.

Identifies methods that use more features of another class than
their own class, suggesting they should be moved.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("move_method", category="refactoring", severity="medium")
@param("threshold", float, default=0.6, description="External usage ratio threshold")
@param("limit", int, default=100, description="Maximum results to return")
def move_method() -> Pipeline:
    """
    Suggest Move Method refactoring opportunities.

    Returns:
        findings: List of methods that should be moved
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?target_class ?external_usage
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m definedIn ?c .
                ?c name ?class_name .
                ?m primaryExternalClass ?target .
                ?target name ?target_class .
                ?m externalUsageRatio ?external_usage
            FILTER ( ?external_usage > {threshold} )
            }
            ORDER BY DESC(?external_usage)
        ''')
        .select("name", "class_name", "file", "line", "target_class", "external_usage", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "move_method",
            "message": f"Method '{r['name']}' uses '{r.get('target_class', 'unknown')}' more than its own class",
            "suggestion": f"Consider moving this method to {r.get('target_class', 'the target class')}"
        })
        .emit("findings")
    )

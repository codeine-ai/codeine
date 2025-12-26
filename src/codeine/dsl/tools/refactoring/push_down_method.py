"""
push_down_method - Suggest Push Down Method refactoring opportunities.

Identifies methods in a parent class that are only used by some
subclasses and could be pushed down to those specific subclasses.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("push_down_method", category="refactoring", severity="low")
@param("limit", int, default=100, description="Maximum results to return")
def push_down_method() -> Pipeline:
    """
    Suggest Push Down Method refactoring opportunities.

    Returns:
        findings: List of methods that could be pushed down
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m definedIn ?c .
                ?c name ?class_name .
                ?sub inheritsFrom ?c .
            }
        ''')
        .select("name", "class_name", "file", "line", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "push_down_method",
            "message": f"Method '{r['name']}' in '{r.get('class_name', 'unknown')}' may be pushable to subclasses",
            "suggestion": "Consider pushing this method down to the subclasses that use it"
        })
        .emit("findings")
    )

"""
move_field - Detect fields that belong in a different class.

A field should be in the class that uses it most. If a field is used
more by another class, it's a candidate for Move Field refactoring.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("move_field", category="refactoring", severity="medium")
@param("min_external_ratio", float, default=0.6, description="Minimum external usage ratio")
@param("limit", int, default=100, description="Maximum results to return")
def move_field() -> Pipeline:
    """
    Detect fields that are used more by other classes than their own.

    Returns:
        findings: List of fields that should be moved
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?attr ?name ?class_name ?target_class ?file ?line ?own_usage ?external_usage
            WHERE {
                ?attr type {Attribute} .
                ?attr name ?name .
                ?attr definedIn ?c .
                ?c name ?class_name .
                ?attr inFile ?file .
                ?attr atLine ?line .
                ?attr ownClassUsage ?own_usage .
                ?attr externalClassUsage ?external_usage .
                ?attr topExternalClass ?target_class .
                FILTER ( !STRSTARTS(?name, "_") )
            }
        ''')
        .select("name", "class_name", "target_class", "file", "line", "own_usage", "external_usage")
        .map(lambda r: {
            **r,
            "ratio": float(r.get('external_usage', 0)) / (float(r.get('own_usage', 0)) + float(r.get('external_usage', 0)) + 0.001),
            "refactoring": "move_field",
            "message": f"Field '{r['class_name']}.{r['name']}' used {r['external_usage']} times by '{r['target_class']}' vs {r['own_usage']} own uses",
            "suggestion": f"Move field to '{r['target_class']}'"
        })
        .filter(lambda r, p: r.get('ratio', 0) >= float(p.get('min_external_ratio', 0.6)))
        .emit("findings")
    )

"""
shotgun_surgery - Detect changes that require touching many classes.

Shotgun Surgery occurs when a change requires making many small
changes to many different classes. This indicates high coupling.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("shotgun_surgery", category="design", severity="high")
@param("min_dependents", int, default=5, description="Minimum dependents to flag")
@param("limit", int, default=100, description="Maximum results to return")
def shotgun_surgery() -> Pipeline:
    """
    Detect code that would require shotgun surgery to change.

    Returns:
        findings: List of classes/methods with high change impact
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?file ?line (COUNT(?caller) AS ?dependent_count)
            WHERE {
                { ?e type {Class} } UNION { ?e type {Method} }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                ?caller calls ?e .
            }
            GROUP BY ?e ?name ?file ?line
            HAVING (?dependent_count >= {min_dependents})
            ORDER BY DESC(?dependent_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "dependent_count", qualified_name="e")
        .map(lambda r: {
            **r,
            "issue": "shotgun_surgery",
            "message": f"'{r['name']}' has {r['dependent_count']} callers",
            "suggestion": "Changes here would require updating many files. Consider consolidating or decoupling."
        })
        .emit("findings")
    )

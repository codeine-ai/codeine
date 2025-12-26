"""
speculative_generality - Detect abstract classes with only one subclass.

Speculative generality occurs when code is made more abstract than necessary
"just in case" it might be needed, but the flexibility is never used.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("speculative_generality", category="code_smell", severity="low")
@param("limit", int, default=100, description="Maximum results to return")
def speculative_generality() -> Pipeline:
    """
    Detect speculative generality - unnecessary abstraction.

    Returns:
        findings: List of abstract classes with single subclass
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line ?subclass_name (COUNT(?sub) AS ?subclass_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c isAbstract true .
                ?sub inheritsFrom ?c .
                ?sub name ?subclass_name .
            }
            GROUP BY ?c ?name ?file ?line ?subclass_name
            HAVING (?subclass_count = 1)
            ORDER BY ?file ?line
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "subclass_name", "subclass_count")
        .map(lambda r: {
            **r,
            "issue": "speculative_generality",
            "message": f"Abstract class '{r['name']}' has only one subclass: '{r.get('subclass_name', 'unknown')}'",
            "suggestion": "Consider collapsing hierarchy or waiting until you need the abstraction"
        })
        .emit("findings")
    )

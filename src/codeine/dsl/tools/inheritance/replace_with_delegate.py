"""
replace_with_delegate_candidates - Find inheritance with low coupling (refused bequest).

Identifies classes that inherit but use very little of the parent,
suggesting delegation might be more appropriate.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("replace_with_delegate_candidates", category="inheritance", severity="medium")
@param("max_parent_calls", int, default=2, description="Maximum parent method calls")
@param("limit", int, default=100, description="Maximum results to return")
def replace_with_delegate_candidates() -> Pipeline:
    """
    Find inheritance that should be replaced with delegation.

    Returns:
        findings: List of replace with delegate opportunities
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?parent_name ?file ?line (COUNT(?parent_call) AS ?parent_usage)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c inheritsFrom ?parent .
                ?parent name ?parent_name .
                ?method definedIn ?c .
                ?method calls ?parent_method .
                ?parent_method definedIn ?parent .
                            }
            GROUP BY ?c ?name ?parent_name ?file ?line
            HAVING (?parent_usage > 0 && ?parent_usage <= {max_parent_calls})
            ORDER BY ?parent_usage
            LIMIT {limit}
        ''')
        .select("name", "parent_name", "file", "line", "parent_usage")
        .map(lambda r: {
            **r,
            "refactoring": "replace_inheritance_with_delegation",
            "message": f"Class '{r['name']}' uses only {r.get('parent_usage', 0)} parent methods",
            "suggestion": f"Replace inheritance from '{r.get('parent_name', '')}' with delegation"
        })
        .emit("findings")
    )

"""
replace_inheritance_with_delegation - Suggest delegation over inheritance.

Identifies classes that inherit but only use a small portion of the
parent class, suggesting delegation might be more appropriate.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("replace_inheritance_with_delegation", category="refactoring", severity="medium")
@param("max_parent_calls", int, default=2, description="Maximum calls to parent methods")
@param("limit", int, default=100, description="Maximum results to return")
def replace_inheritance_with_delegation() -> Pipeline:
    """
    Suggest Replace Inheritance with Delegation opportunities.

    Returns:
        findings: List of classes that might benefit from delegation
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
        .select("name", "parent_name", "file", "line", "parent_usage", qualified_name="c")
        .map(lambda r: {
            **r,
            "refactoring": "replace_inheritance_with_delegation",
            "message": f"Class '{r['name']}' uses only {r.get('parent_usage', 0)} parent methods",
            "suggestion": f"Consider using delegation instead of inheriting from '{r.get('parent_name', 'parent')}'"
        })
        .emit("findings")
    )

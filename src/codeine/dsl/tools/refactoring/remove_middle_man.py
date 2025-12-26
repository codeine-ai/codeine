"""
remove_middle_man - Suggest Remove Middle Man refactoring opportunities.

Identifies classes that delegate most of their methods to another
class, acting as unnecessary intermediaries.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("remove_middle_man", category="refactoring", severity="low")
@param("min_delegations", int, default=5, description="Minimum delegating methods")
@param("limit", int, default=100, description="Maximum results to return")
def remove_middle_man() -> Pipeline:
    """
    Suggest Remove Middle Man refactoring opportunities.

    Returns:
        findings: List of classes that are pure delegates
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line ?delegate_class (COUNT(?delegation) AS ?delegation_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?delegation type {Method} .
                ?delegation definedIn ?c .
                ?delegation calls ?target .
                ?target definedIn ?delegate .
                ?delegate name ?delegate_class .
                FILTER ( ?delegate != ?c )
            }
            GROUP BY ?c ?name ?file ?line ?delegate_class
            HAVING (?delegation_count >= {min_delegations})
            ORDER BY DESC(?delegation_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "delegate_class", "delegation_count", qualified_name="c")
        .map(lambda r: {
            **r,
            "refactoring": "remove_middle_man",
            "message": f"Class '{r['name']}' delegates {r['delegation_count']} calls to '{r.get('delegate_class', 'unknown')}'",
            "suggestion": "Consider removing this middle man and having clients call the delegate directly"
        })
        .emit("findings")
    )

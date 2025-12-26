"""
hide_delegate - Detect opportunities to hide internal object delegation.

When a client calls a method on an object to get another object, then calls
a method on that object, consider adding a delegating method to hide the chain.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("hide_delegate", category="refactoring", severity="medium")
@param("limit", int, default=100, description="Maximum results to return")
def hide_delegate() -> Pipeline:
    """
    Detect opportunities to add delegating methods to hide dependencies.

    Finds methods that return objects (have returnType) which are then
    called by other methods - suggesting delegation hiding opportunity.

    Returns:
        findings: List of delegate hiding opportunities
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?class_name ?getter_name ?return_type ?file ?line (COUNT(?caller) AS ?usage_count)
            WHERE {
                ?c type {Class} .
                ?c name ?class_name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?getter type {Method} .
                ?getter definedIn ?c .
                ?getter name ?getter_name .
                ?getter returnType ?return_type .
                ?caller calls ?getter .
                FILTER ( STRSTARTS(?getter_name, "get_") || STRSTARTS(?getter_name, "get") )
            }
            GROUP BY ?c ?class_name ?getter_name ?return_type ?file ?line
            HAVING (?usage_count >= 2)
            ORDER BY DESC(?usage_count)
            LIMIT {limit}
        ''')
        .select("class_name", "getter_name", "return_type", "usage_count", "file", "line")
        .map(lambda r: {
            **r,
            "refactoring": "hide_delegate",
            "message": f"Getter '{r['getter_name']}' in '{r['class_name']}' returns '{r.get('return_type', 'object')}' ({r['usage_count']} usages)",
            "suggestion": f"Add delegating methods to '{r['class_name']}' to hide the delegate"
        })
        .emit("findings")
    )

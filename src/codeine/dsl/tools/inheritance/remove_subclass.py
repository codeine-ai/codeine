"""
remove_subclass_candidates - Find trivial subclasses that can be removed.

Identifies subclasses that add minimal value and could be replaced
with configuration or removed entirely.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("remove_subclass_candidates", category="inheritance", severity="low")
@param("max_methods", int, default=2, description="Maximum methods for trivial subclass")
@param("limit", int, default=100, description="Maximum results to return")
def remove_subclass_candidates() -> Pipeline:
    """
    Find trivial subclasses that could be removed.

    Returns:
        findings: List of trivial subclasses
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?parent_name ?file ?line (COUNT(?method) AS ?method_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c inheritsFrom ?parent .
                ?parent name ?parent_name .
                OPTIONAL { ?method type {Method} . ?method definedIn ?c }
            }
            GROUP BY ?c ?name ?parent_name ?file ?line
            HAVING (?method_count <= {max_methods})
            ORDER BY ?method_count
            LIMIT {limit}
        ''')
        .select("name", "parent_name", "file", "line", "method_count")
        .map(lambda r: {
            **r,
            "refactoring": "remove_subclass",
            "message": f"Subclass '{r['name']}' has only {r.get('method_count', 0)} methods",
            "suggestion": f"Consider removing and using '{r.get('parent_name', 'parent')}' with configuration"
        })
        .emit("findings")
    )

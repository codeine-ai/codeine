"""
collapse_hierarchy_candidates - Find nearly identical parent-child pairs.

Identifies inheritance hierarchies where child adds minimal value
and could be collapsed into the parent.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("collapse_hierarchy_candidates", category="inheritance", severity="low")
@param("max_added_methods", int, default=1, description="Maximum methods added by child")
@param("limit", int, default=100, description="Maximum results to return")
def collapse_hierarchy_candidates() -> Pipeline:
    """
    Find parent-child class pairs that could be collapsed.

    Returns:
        findings: List of collapse hierarchy opportunities
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?child ?child_name ?parent_name ?file ?line (COUNT(?added_method) AS ?added_methods)
            WHERE {
                ?child type {Class} .
                ?child name ?child_name .
                ?child inFile ?file .
                ?child atLine ?line .
                ?child inheritsFrom ?parent .
                ?parent name ?parent_name .
                ?added_method type {Method} .
                ?added_method definedIn ?child .
                ?added_method name ?method_name .
                FILTER ( !STRSTARTS(?method_name, "_") )
            }
            GROUP BY ?child ?child_name ?parent_name ?file ?line
            HAVING (?added_methods <= {max_added_methods})
            ORDER BY ?added_methods
            LIMIT {limit}
        ''')
        .select("child_name", "parent_name", "file", "line", "added_methods")
        .map(lambda r: {
            **r,
            "refactoring": "collapse_hierarchy",
            "message": f"Class '{r['child_name']}' adds only {r.get('added_methods', 0)} methods to parent '{r.get('parent_name', '')}'",
            "suggestion": "Consider collapsing child into parent"
        })
        .emit("findings")
    )

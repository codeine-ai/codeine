"""
inline_class - Detect small, trivial classes that should be inlined.

Classes that do very little can add unnecessary complexity.
If a class is barely doing anything, its features can be moved into another class.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("inline_class", category="refactoring", severity="low")
@param("max_methods", int, default=2, description="Maximum methods for trivial class")
@param("max_attributes", int, default=2, description="Maximum attributes for trivial class")
@param("limit", int, default=100, description="Maximum results to return")
def inline_class() -> Pipeline:
    """
    Detect trivial classes that could be inlined into their users.

    Returns:
        findings: List of classes that are candidates for inlining
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?method) AS ?method_count) (COUNT(?attr) AS ?attr_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                OPTIONAL { ?method type {Method} . ?method definedIn ?c }
                OPTIONAL { ?attr type {Field} . ?attr definedIn ?c }
                FILTER ( !REGEX(?name, "Exception$|Error$|Config$|Settings$") )
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?method_count <= {max_methods} && ?attr_count <= {max_attributes})
            ORDER BY ?method_count ?attr_count
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "method_count", "attr_count")
        .map(lambda r: {
            **r,
            "refactoring": "inline_class",
            "message": f"Class '{r['name']}' is trivial ({r['method_count']} methods, {r['attr_count']} attributes)",
            "suggestion": "Consider inlining this class into its users"
        })
        .emit("findings")
    )

"""
duplicate_parameter_lists - Detect functions with identical parameter signatures.

Functions with the same parameter list often indicate a missing abstraction
or opportunity to introduce a parameter object.

Note: This detector finds functions/methods with similar parameter patterns
by looking at parameter counts and types.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("duplicate_parameter_lists", category="refactoring", severity="medium")
@param("min_params", int, default=3, description="Minimum parameters to consider")
@param("limit", int, default=100, description="Maximum results to return")
def duplicate_parameter_lists() -> Pipeline:
    """
    Detect functions sharing similar parameter signatures.

    Returns:
        findings: List of functions with many parameters (candidates for parameter objects)
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line (COUNT(?param) AS ?param_count)
            WHERE {
                { ?m type {Method} } UNION { ?m type {Function} }
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?param type {Parameter} .
                ?param ofFunction ?m .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name }
            }
            GROUP BY ?m ?name ?class_name ?file ?line
            HAVING (?param_count >= {min_params})
            ORDER BY DESC(?param_count)
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "param_count", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "introduce_parameter_object",
            "message": f"Function '{r['name']}' has {r['param_count']} parameters",
            "suggestion": "Introduce a parameter object to group these parameters"
        })
        .emit("findings")
    )

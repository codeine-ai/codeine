"""
introduce_parameter_object - Suggest Introduce Parameter Object refactoring.

Identifies methods with many parameters that could benefit from
grouping related parameters into a parameter object.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("introduce_parameter_object", category="refactoring", severity="medium")
@param("min_params", int, default=4, description="Minimum parameters to suggest")
@param("limit", int, default=100, description="Maximum results to return")
def introduce_parameter_object() -> Pipeline:
    """
    Suggest Introduce Parameter Object refactoring opportunities.

    Returns:
        findings: List of methods with many parameters
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
            "message": f"Method '{r['name']}' has {r['param_count']} parameters",
            "suggestion": "Consider grouping related parameters into a parameter object"
        })
        .emit("findings")
    )

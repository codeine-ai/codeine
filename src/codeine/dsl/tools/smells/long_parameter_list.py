"""
long_parameter_list - Detect methods with too many parameters.

Methods with many parameters are hard to understand and use correctly.
Consider using parameter objects or builder patterns.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("long_parameter_list", category="complexity", severity="low")
@param("max_params", int, default=5, description="Maximum parameters before flagging")
@param("limit", int, default=100, description="Maximum results to return")
def long_parameter_list() -> Pipeline:
    """
    Detect methods with too many parameters.

    Returns:
        findings: List of methods with long parameter lists
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?file ?line (COUNT(?param) AS ?param_count)
            WHERE {
                { ?m type {Method} } UNION { ?m type {Function} }
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?param type {Parameter} .
                ?param ofFunction ?m .
            }
            GROUP BY ?m ?name ?file ?line
            HAVING (?param_count > {max_params})
            ORDER BY DESC(?param_count)
        ''')
        .select("name", "file", "line", "param_count", qualified_name="m")
        .map(lambda r: {
            **r,
            "issue": "long_parameter_list",
            "message": f"'{r['name']}' has {r['param_count']} parameters",
            "suggestion": "Consider using a parameter object or builder pattern"
        })
        .emit("findings")
    )

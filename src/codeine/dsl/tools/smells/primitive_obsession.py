"""
primitive_obsession - Detect overuse of primitive types.

Using primitives for domain concepts leads to scattered validation
and business logic. Consider using value objects or domain types.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("primitive_obsession", category="design", severity="low")
@param("min_primitives", int, default=3, description="Minimum primitive params to flag")
@param("limit", int, default=100, description="Maximum results to return")
def primitive_obsession() -> Pipeline:
    """
    Detect overuse of primitive types for domain concepts.

    Returns:
        findings: List of potential primitive obsession cases
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line (COUNT(?primitive_param) AS ?primitive_params)
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m definedIn ?c .
                ?c name ?class_name .
                ?primitive_param type {Parameter} .
                ?primitive_param ofFunction ?m .
                ?primitive_param typeAnnotation ?ptype .
                FILTER ( REGEX(?ptype, "^(str|int|float|bool|bytes)$") )
            }
            GROUP BY ?m ?name ?class_name ?file ?line
            HAVING (?primitive_params >= {min_primitives})
            ORDER BY DESC(?primitive_params)
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "primitive_params", qualified_name="m")
        .map(lambda r: {
            **r,
            "issue": "primitive_obsession",
            "message": f"Method '{r['name']}' has {r['primitive_params']} primitive parameters",
            "suggestion": "Consider using value objects for domain concepts"
        })
        .emit("findings")
    )

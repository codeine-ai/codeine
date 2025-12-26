"""
undocumented_code - Detect public classes and functions without docstrings.

Documentation is essential for maintainability. Public APIs should
always have docstrings explaining purpose, parameters, and return values.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("undocumented_code", category="code_smell", severity="low")
@param("include_private", bool, default=False, description="Include private members")
@param("limit", int, default=100, description="Maximum results to return")
def undocumented_code() -> Pipeline:
    """
    Detect undocumented public classes and functions.

    Returns:
        findings: List of undocumented code entities
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?type ?file ?line ?class_name
            WHERE {
                {
                    ?e type {Class} .
                                    } UNION {
                    ?e type {Function} .
                                    } UNION {
                    ?e type {Method} .
                    ?e definedIn ?c .
                    ?c name ?class_name .
                                    }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                ?e hasDocstring false .
                FILTER ( {include_private} || !STRSTARTS(?name, "_") )
                FILTER ( !REGEX(?file, "test") )
            }
            ORDER BY ?file ?line
            LIMIT {limit}
        ''')
        .select("name", "type", "file", "line", "class_name")
        .map(lambda r: {
            **r,
            "issue": "undocumented",
            "message": f"Undocumented {r['type']}: '{r['name']}'" + (f" in {r['class_name']}" if r.get('class_name') else ""),
            "suggestion": "Add a docstring explaining purpose, parameters, and return value"
        })
        .emit("findings")
    )

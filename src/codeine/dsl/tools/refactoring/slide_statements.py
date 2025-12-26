"""
slide_statements - Detect statements accessing same data but separated by unrelated code.

Related statements should be grouped together for clarity.
When statements operating on the same data are separated, consider sliding them together.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("slide_statements", category="refactoring", severity="low")
@param("min_distance", int, default=5, description="Minimum lines between related statements")
@param("limit", int, default=100, description="Maximum results to return")
def slide_statements() -> Pipeline:
    """
    Detect separated statements that should be grouped together.

    Returns:
        findings: List of statement pairs that should be slid together
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?func ?func_name ?var_name ?first_line ?second_line ?distance ?file
            WHERE {
                ?pair type {SeparatedStatements} .
                ?pair inFunction ?func .
                ?func name ?func_name .
                ?pair variableName ?var_name .
                ?pair firstLine ?first_line .
                ?pair secondLine ?second_line .
                ?pair distance ?distance .
                ?func inFile ?file .
            FILTER ( ?distance >= {min_distance} )
            }
            ORDER BY DESC(?distance)
            LIMIT {limit}
        ''')
        .select("func_name", "var_name", "first_line", "second_line", "distance", "file")
        .map(lambda r: {
            **r,
            "refactoring": "slide_statements",
            "message": f"Statements using '{r['var_name']}' at lines {r['first_line']} and {r['second_line']} are {r['distance']} lines apart",
            "suggestion": "Slide statements together to group related operations"
        })
        .emit("findings")
    )

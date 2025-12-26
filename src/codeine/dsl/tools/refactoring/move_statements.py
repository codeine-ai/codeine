"""
move_statements - Detect repeated statement sequences before/after function calls.

When the same statements appear before or after calls to a function,
they should be moved into the function itself.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("move_statements", category="refactoring", severity="medium")
@param("min_occurrences", int, default=2, description="Minimum occurrences of pattern")
@param("limit", int, default=100, description="Maximum results to return")
def move_statements() -> Pipeline:
    """
    Detect repeated statements that should be moved into a function.

    Returns:
        findings: List of statement patterns to move
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?func ?func_name ?pattern ?position ?occurrence_count ?callers ?file ?line
            WHERE {
                ?pattern type {CallSitePattern} .
                ?pattern targetFunction ?func .
                ?func name ?func_name .
                ?pattern statements ?statements .
                ?pattern position ?position .
                ?pattern occurrenceCount ?occurrence_count .
                ?pattern callers ?callers .
                ?func inFile ?file .
                ?func atLine ?line .
            FILTER ( ?occurrence_count >= {min_occurrences} )
            }
            ORDER BY DESC(?occurrence_count)
            LIMIT {limit}
        ''')
        .select("func_name", "position", "occurrence_count", "callers", "file", "line")
        .map(lambda r: {
            **r,
            "refactoring": "move_statements_into_function",
            "message": f"Statements {r['position']} '{r['func_name']}' appear in {r['occurrence_count']} call sites",
            "suggestion": f"Move these statements into '{r['func_name']}'"
        })
        .emit("findings")
    )

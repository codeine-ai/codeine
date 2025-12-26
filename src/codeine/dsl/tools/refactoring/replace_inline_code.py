"""
replace_inline_code - Detect duplicate statement sequences replaceable with function calls.

When the same sequence of statements appears in multiple places,
it should be extracted into a function.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("replace_inline_code", category="refactoring", severity="medium")
@param("min_statements", int, default=3, description="Minimum statements in sequence")
@param("min_occurrences", int, default=2, description="Minimum occurrences")
@param("limit", int, default=100, description="Maximum results to return")
def replace_inline_code() -> Pipeline:
    """
    Detect duplicate code sequences that should be extracted to a function.

    Returns:
        findings: List of duplicate sequences
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?pattern ?statement_count ?occurrence_count ?locations ?first_file ?first_line
            WHERE {
                ?pattern type {CodePattern} .
                ?pattern statementCount ?statement_count .
                ?pattern occurrenceCount ?occurrence_count .
                ?pattern locations ?locations .
                ?pattern firstFile ?first_file .
                ?pattern firstLine ?first_line .
            FILTER ( ?statement_count >= {min_statements} && ?occurrence_count >= {min_occurrences} )
            }
            ORDER BY DESC(?occurrence_count) DESC(?statement_count)
            LIMIT {limit}
        ''')
        .select("statement_count", "occurrence_count", "locations", "first_file", "first_line")
        .map(lambda r: {
            **r,
            "file": r["first_file"],
            "line": r["first_line"],
            "refactoring": "extract_function",
            "message": f"Code sequence ({r['statement_count']} statements) appears {r['occurrence_count']} times",
            "suggestion": "Extract to a function and replace inline code with function calls"
        })
        .emit("findings")
    )

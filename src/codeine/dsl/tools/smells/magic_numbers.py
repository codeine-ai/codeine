"""
magic_numbers - Detect numeric literals that should be named constants.

Magic numbers are unexplained numeric literals in code that make it harder
to understand intent and maintain consistency.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("magic_numbers", category="code_smell", severity="medium")
@param("exclude_common", bool, default=True, description="Exclude common values like 0, 1, -1")
@param("min_occurrences", int, default=2, description="Minimum occurrences to report")
@param("limit", int, default=100, description="Maximum results to return")
def magic_numbers() -> Pipeline:
    """
    Detect magic numbers - numeric literals that should be named constants.

    Returns:
        findings: List of magic numbers with locations and occurrence counts
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?value ?occurrences ?files ?locations
            WHERE {
                ?lit type {NumericLiteral} .
                ?lit value ?value .
                ?lit occurrenceCount ?occurrences .
                ?lit distinctFiles ?files .
                ?lit locations ?locations .
                FILTER ( !{exclude_common} || (?value != 0 && ?value != 1 && ?value != -1 && ?value != 2) )
                FILTER ( ?occurrences >= {min_occurrences} )
            }
            ORDER BY DESC(?occurrences)
            LIMIT {limit}
        ''')
        .select("value", "occurrences", "files", "locations")
        .map(lambda r: {
            **r,
            "issue": "magic_number",
            "message": f"Magic number '{r['value']}' appears {r['occurrences']} times across {r.get('files', 1)} files",
            "suggestion": "Extract to a named constant with a descriptive name"
        })
        .emit("findings")
    )

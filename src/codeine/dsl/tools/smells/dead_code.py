"""
dead_code - Detect unused classes, methods, and functions.

Dead code adds maintenance burden and can confuse developers.
It should be removed to keep the codebase clean.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("dead_code", category="maintenance", severity="low")
@param("include_private", bool, default=False, description="Include private methods")
@param("limit", int, default=100, description="Maximum results to return")
def dead_code() -> Pipeline:
    """
    Detect unused classes, methods, and functions.

    Returns:
        findings: List of potentially dead code
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?entity_type ?file ?line
            WHERE {
                { ?e type {Method} } UNION { ?e type {Function} }
                ?e type ?entity_type .
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                FILTER NOT EXISTS { ?caller calls ?e }
                FILTER ( !REGEX(?name, "^__") )
            }
            ORDER BY ?file ?line
        ''')
        .select("name", "entity_type", "file", "line", qualified_name="e")
        .map(lambda r: {
            **r,
            "issue": "dead_code",
            "message": f"Unused {r['entity_type']} '{r['name']}' - no callers found",
            "suggestion": "Consider removing if truly unused"
        })
        .emit("findings")
    )

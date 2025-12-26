"""
global_data - Detect module-level mutable data.

Global mutable data makes code harder to reason about and test.
It can lead to hidden dependencies and unexpected side effects.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("global_data", category="code_smell", severity="high")
@param("limit", int, default=100, description="Maximum results to return")
def global_data() -> Pipeline:
    """
    Detect global mutable data - module-level assignments.

    Returns:
        findings: List of module-level assignments (potential globals)
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?a ?target ?value ?file ?line
            WHERE {
                ?a type {Assignment} .
                ?a target ?target .
                ?a value ?value .
                ?a inFile ?file .
                ?a atLine ?line .
                FILTER NOT EXISTS { ?a inFunction ?f }
                FILTER NOT EXISTS { ?a inClass ?c }
                FILTER ( !STRSTARTS(?target, "_") )
                FILTER ( !REGEX(?target, "^[A-Z_]+$") )
            }
            ORDER BY ?file ?line
            LIMIT {limit}
        ''')
        .select("target", "value", "file", "line")
        .map(lambda r: {
            **r,
            "name": r.get("target"),
            "issue": "global_mutable_data",
            "message": f"Module-level assignment '{r.get('target')}' may be mutable global data",
            "suggestion": "Encapsulate in a class, use dependency injection, or make immutable (CONSTANT_CASE)"
        })
        .emit("findings")
    )

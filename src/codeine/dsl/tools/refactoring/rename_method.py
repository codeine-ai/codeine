"""
rename_method - Suggest Rename Method refactoring opportunities.

Identifies methods with unclear or inconsistent names that could
benefit from renaming.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("rename_method", category="refactoring", severity="low")
@param("min_length", int, default=1, description="Minimum name length (single chars flagged)")
@param("max_length", int, default=50, description="Maximum reasonable name length")
@param("limit", int, default=100, description="Maximum results to return")
def rename_method() -> Pipeline:
    """
    Suggest Rename Method refactoring opportunities.

    Returns:
        findings: List of methods with unclear names
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name }
                FILTER ( REGEX(?name, "^(do|process|handle|execute|run)$") )
            }
        ''')
        .select("name", "class_name", "file", "line", qualified_name="m")
        .map(lambda r: {
            **r,
            "name_length": len(r.get('name', '')),
            "refactoring": "rename_method",
            "message": f"Method '{r['name']}' has an unclear name",
            "suggestion": "Use a more descriptive name that explains what the method does"
        })
        .emit("findings")
    )

"""
find_unused_imports - Find imported modules/symbols that are never used.

Identifies imports that can be removed to clean up the code.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_unused_imports", category="dependencies", severity="low")
@param("limit", int, default=100, description="Maximum results to return")
def find_unused_imports() -> Pipeline:
    """
    Find unused imports that can be removed.

    Returns:
        findings: List of unused imports
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?i ?import_name ?file ?line
            WHERE {
                ?i type {Import} .
                ?i name ?import_name .
                ?i inFile ?file .
                ?i atLine ?line .
                ?i isUsed false.
            }
            ORDER BY ?file ?line
        ''')
        .select("import_name", "file", "line")
        .map(lambda r: {
            **r,
            "issue": "unused_import",
            "message": f"Unused import '{r['import_name']}'",
            "suggestion": "Remove the unused import"
        })
        .emit("findings")
    )

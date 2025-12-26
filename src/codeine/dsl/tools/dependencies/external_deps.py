"""
find_external_dependencies - Find external package dependencies.

Identifies all external (pip) packages used in the codebase.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_external_dependencies", category="dependencies", severity="info")
@param("limit", int, default=100, description="Maximum results to return")
def find_external_dependencies() -> Pipeline:
    """
    Find external package dependencies.

    Returns:
        findings: List of external packages used
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?i ?package_name ?file ?line ?usage_count
            WHERE {
                ?i type {Import} .
                ?i name ?package_name .
                ?i inFile ?file .
                ?i atLine ?line .
                ?i isExternal true.
                OPTIONAL { ?i usageCount ?usage_count }
            }
            ORDER BY ?package_name
        ''')
        .select("package_name", "file", "line", "usage_count")
        .unique(lambda r: r.get("package_name"))
        .emit("findings")
    )

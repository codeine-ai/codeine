"""
find_singleton_pattern - Find classes implementing singleton pattern.

Identifies classes that use singleton pattern implementation.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_singleton_pattern", category="patterns", severity="info")
@param("limit", int, default=100, description="Maximum results to return")
def find_singleton_pattern() -> Pipeline:
    """
    Find classes implementing singleton pattern.

    Returns:
        findings: List of singleton classes
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line ?implementation_type
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c isSingleton true.
                OPTIONAL { ?c singletonType ?implementation_type }
            }
            ORDER BY ?file ?line
        ''')
        .select("name", "file", "line", "implementation_type")
        .emit("findings")
    )

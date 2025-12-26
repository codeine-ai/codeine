"""
find_magic_methods - Find all magic/dunder methods in the codebase.

Identifies __init__, __str__, __repr__, and other magic methods.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_magic_methods", category="patterns", severity="info")
@param("limit", int, default=100, description="Maximum results to return")
def find_magic_methods() -> Pipeline:
    """
    Find all magic/dunder methods in the codebase.

    Returns:
        findings: List of magic methods
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?method_name ?class_name ?file ?line
            WHERE {
                ?m type {Method} .
                ?m name ?method_name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m definedIn ?c .
                ?c name ?class_name
            FILTER ( REGEX(?method_name, "^__.*__$") )
            }
            ORDER BY ?class_name ?method_name
        ''')
        .select("method_name", "class_name", "file", "line")
        .emit("findings")
    )

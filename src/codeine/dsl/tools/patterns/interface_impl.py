"""
find_interface_implementations - Find classes implementing interfaces/ABCs.

Identifies classes that implement abstract base classes or protocols.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_interface_implementations", category="patterns", severity="info")
@param("interface_name", str, required=False, default=None, description="Filter by interface name")
@param("limit", int, default=100, description="Maximum results to return")
def find_interface_implementations() -> Pipeline:
    """
    Find classes implementing abstract base classes or interfaces.

    Returns:
        findings: List of interface implementations
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?class_name ?interface_name ?file ?line ?implemented_methods
            WHERE {
                ?c type {Class} .
                ?c name ?class_name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c inheritsFrom ?interface .
                ?interface name ?interface_name .
                ?interface isAbstract true.
                OPTIONAL { ?c implementedMethodCount ?implemented_methods }
            }
            ORDER BY ?interface_name ?class_name
        ''')
        .select("class_name", "interface_name", "file", "line", "implemented_methods")
        .emit("findings")
    )

"""
trivial_commands - Detect trivial command objects that should be functions.

The Command pattern is useful for undo/redo and queuing, but trivial
command classes that just wrap a single call add unnecessary complexity.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("trivial_commands", category="code_smell", severity="low")
@param("max_methods", int, default=2, description="Maximum methods for trivial command")
@param("max_lines", int, default=5, description="Maximum lines in execute method")
@param("limit", int, default=100, description="Maximum results to return")
def trivial_commands() -> Pipeline:
    """
    Detect trivial command classes that should be simple functions.

    Returns:
        findings: List of trivial command objects
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?method) AS ?method_count) ?execute_lines
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?method type {Method} .
                ?method definedIn ?c .
                ?c hasMethod ?exec .
                ?exec name ?exec_name .
                ?exec lineCount ?execute_lines .
                FILTER ( ?exec_name = "execute" || ?exec_name = "run" || ?exec_name = "__call__" )
                FILTER ( REGEX(?name, "Command$|Action$|Task$") )
            }
            GROUP BY ?c ?name ?file ?line ?execute_lines
            HAVING (?method_count <= {max_methods} && ?execute_lines <= {max_lines})
            ORDER BY ?execute_lines
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "method_count", "execute_lines")
        .map(lambda r: {
            **r,
            "issue": "trivial_command",
            "message": f"Command class '{r['name']}' is trivial ({r['execute_lines']} lines, {r['method_count']} methods)",
            "suggestion": "Replace with a simple function unless you need undo/redo or queuing"
        })
        .emit("findings")
    )

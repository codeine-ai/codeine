"""
extract_method - Suggest Extract Method refactoring opportunities.

Identifies long methods or methods with extractable code blocks
that could be refactored into smaller, reusable methods.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("extract_method", category="refactoring", severity="medium")
@param("min_lines", int, default=20, description="Minimum lines to suggest extraction")
@param("limit", int, default=100, description="Maximum results to return")
def extract_method() -> Pipeline:
    """
    Suggest Extract Method refactoring opportunities.

    Returns:
        findings: List of methods that could benefit from extraction
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?line_count ?block_count
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m lineCount ?line_count .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name }
                OPTIONAL { ?m codeBlockCount ?block_count                     FILTER ( ?line_count >= {min_lines} )
                }
            }
            ORDER BY DESC(?line_count)
        ''')
        .select("name", "class_name", "file", "line", "line_count", "block_count", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "extract_method",
            "message": f"Method '{r['name']}' ({r['line_count']} lines) may benefit from Extract Method",
            "suggestion": "Identify cohesive code blocks and extract them into well-named methods"
        })
        .emit("findings")
    )

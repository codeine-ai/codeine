"""
inline_method - Suggest Inline Method refactoring opportunities.

Identifies very short methods that are only called from one place
and could be inlined to simplify the code.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("inline_method", category="refactoring", severity="low")
@param("max_lines", int, default=3, description="Maximum lines for inline candidate")
@param("max_callers", int, default=1, description="Maximum callers for inline candidate")
@param("limit", int, default=100, description="Maximum results to return")
def inline_method() -> Pipeline:
    """
    Suggest Inline Method refactoring opportunities.

    Returns:
        findings: List of methods that could be inlined
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?line_count (COUNT(?caller) AS ?caller_count)
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m lineCount ?line_count .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name }
                OPTIONAL { ?caller calls ?m }
            }
            GROUP BY ?m ?name ?class_name ?file ?line ?line_count
            HAVING (?line_count <= {max_lines} && ?caller_count <= {max_callers})
            ORDER BY ?line_count
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "line_count", "caller_count", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "inline_method",
            "message": f"Method '{r['name']}' ({r['line_count']} lines, {r.get('caller_count', 1)} caller) could be inlined",
            "suggestion": "Consider inlining this simple method if it doesn't add clarity"
        })
        .emit("findings")
    )

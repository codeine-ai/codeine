"""
long_methods - Detect methods that are too long.

Long methods are harder to understand, test, and maintain.
They often indicate that a method is doing too many things.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("long_methods", category="size", severity="medium")
@param("max_lines", int, default=50, description="Maximum lines before flagging")
@param("limit", int, default=100, description="Maximum results to return")
def long_methods() -> Pipeline:
    """
    Detect methods that are too long.

    Returns:
        findings: List of long methods with their metrics
        count: Number of long methods found
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?line_count
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m lineCount ?line_count .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name                 FILTER ( ?line_count > {max_lines} )
            }
            }
            ORDER BY DESC(?line_count)
        ''')
        .select("name", "class_name", "file", "line", "line_count", qualified_name="m")
        .map(lambda r: {
            **r,
            "issue": "long_method",
            "message": f"Method '{r['name']}' has {r['line_count']} lines",
            "suggestion": "Consider extracting smaller methods with clear responsibilities"
        })
        .emit("findings")
    )

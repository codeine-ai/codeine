"""
encapsulate_collection - Detect methods returning mutable collections.

Returning raw mutable collections allows callers to modify internal state.
Collections should be encapsulated with add/remove methods.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("encapsulate_collection", category="refactoring", severity="medium")
@param("limit", int, default=100, description="Maximum results to return")
def encapsulate_collection() -> Pipeline:
    """
    Detect methods returning mutable collections without encapsulation.

    Returns:
        findings: List of methods exposing internal collections
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?return_type ?attr_name
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m definedIn ?c .
                ?c name ?class_name .
                ?m inFile ?file .
                ?m atLine ?line .
                ?m returnType ?return_type .
                ?m returnsAttribute ?attr_name .
                FILTER ( REGEX(?return_type, "list|dict|set|List|Dict|Set|Collection") )
                FILTER ( STRSTARTS(?name, "get") || ?name = ?attr_name )
            }
            ORDER BY ?class_name ?name
            LIMIT {limit}
        ''')
        .select("name", "class_name", "file", "line", "return_type", "attr_name")
        .map(lambda r: {
            **r,
            "refactoring": "encapsulate_collection",
            "message": f"Method '{r['class_name']}.{r['name']}' returns mutable {r['return_type']}",
            "suggestion": "Return a copy or provide add/remove methods instead of exposing the collection"
        })
        .emit("findings")
    )

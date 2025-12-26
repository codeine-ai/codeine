"""
untyped_functions - Detect functions and methods without type hints.

Type hints improve code clarity, enable better IDE support, and allow
static analysis tools to catch bugs earlier.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("untyped_functions")
@param("include_private", bool, default=False, description="Include private functions")
@param("limit", int, default=100, description="Maximum results to return")
def untyped_functions() -> Pipeline:
    """
    Detect functions and methods missing type annotations.

    Returns:
        results: List of untyped functions with annotation status
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?type ?file ?line ?class_name (COUNT(?param) AS ?param_count) (COUNT(?typed_param) AS ?typed_params)
            WHERE {
                {
                    ?e type {Function} .
                                    } UNION {
                    ?e type {Method} .
                    ?e definedIn ?c .
                    ?c name ?class_name .
                                    }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                OPTIONAL { ?param type {Parameter} . ?param ofFunction ?e }
                OPTIONAL { ?typed_param type {Parameter} . ?typed_param ofFunction ?e . ?typed_param typeAnnotation ?ptype }
                FILTER ( {include_private} || !STRSTARTS(?name, "_") )
                FILTER ( !REGEX(?file, "test") )
            }
            GROUP BY ?e ?name ?type ?file ?line ?class_name
            HAVING (?typed_params < ?param_count)
            ORDER BY ?file ?line
            LIMIT {limit}
        ''')
        .select("name", "type", "file", "line", "class_name", "param_count", "typed_params")
        .map(lambda r: {
            **r,
            "missing_param_types": r['param_count'] - r['typed_params'],
            "message": f"{'Method' if r['type'] == 'method' else 'Function'} '{r['name']}' missing {r['param_count'] - r['typed_params']} param types",
            "suggestion": "Add type annotations for better IDE support and static analysis"
        })
        .emit("results")
    )

"""
attribute_data_clumps - Detect groups of attributes appearing together in multiple classes.

When the same group of attributes appears in multiple classes, it often
indicates a missing abstraction that should be extracted into a value object.

Note: This detector finds classes with many attributes that could be grouped.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("attribute_data_clumps", category="refactoring", severity="medium")
@param("min_attributes", int, default=5, description="Minimum attributes to suggest extraction")
@param("limit", int, default=100, description="Maximum results to return")
def attribute_data_clumps() -> Pipeline:
    """
    Detect classes with many attributes that could be grouped into value objects.

    Returns:
        findings: List of classes with attribute clusters
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?attr) AS ?attr_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?attr type {Field} .
                ?attr definedIn ?c .
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?attr_count >= {min_attributes})
            ORDER BY DESC(?attr_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "attr_count", qualified_name="c")
        .map(lambda r: {
            **r,
            "refactoring": "extract_class",
            "message": f"Class '{r['name']}' has {r['attr_count']} attributes",
            "suggestion": "Consider grouping related attributes into value objects/data classes"
        })
        .emit("findings")
    )

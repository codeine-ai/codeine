"""
pull_up_method - Suggest Pull Up Method refactoring opportunities.

Identifies identical or similar methods in sibling classes that
could be pulled up to a common parent class.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("pull_up_method", category="refactoring", severity="medium")
@param("similarity_threshold", float, default=0.9, description="Similarity threshold for detection")
@param("limit", int, default=100, description="Maximum results to return")
def pull_up_method() -> Pipeline:
    """
    Suggest Pull Up Method refactoring opportunities.

    Returns:
        findings: List of methods that could be pulled up
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m1 ?name ?class1 ?class2 ?parent_class ?file ?line ?similarity
            WHERE {
                ?m1 type {Method} .
                ?m1 name ?name .
                ?m1 inFile ?file .
                ?m1 atLine ?line .
                ?m1 definedIn ?c1 .
                ?c1 name ?class1 .
                ?m2 type {Method} .
                ?m2 name ?name .
                ?m2 definedIn ?c2 .
                ?c2 name ?class2 .
                ?c1 inheritsFrom ?parent .
                ?c2 inheritsFrom ?parent .
                ?parent name ?parent_class .
                ?m1 similarTo ?m2 .
                ?m1 similarityScore ?similarity
            FILTER ( ?c1 != ?c2 && ?similarity >= {similarity_threshold} )
            }
            ORDER BY DESC(?similarity)
        ''')
        .select("name", "class1", "class2", "parent_class", "file", "line", "similarity", qualified_name="m1")
        .map(lambda r: {
            **r,
            "refactoring": "pull_up_method",
            "message": f"Method '{r['name']}' is duplicated in '{r.get('class1', '')}' and '{r.get('class2', '')}'",
            "suggestion": f"Consider pulling up to parent class '{r.get('parent_class', 'unknown')}'"
        })
        .emit("findings")
    )

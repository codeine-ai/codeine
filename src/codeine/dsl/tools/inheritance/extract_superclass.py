"""
extract_superclass_candidates - Find classes sharing methods that need a superclass.

Identifies unrelated classes with similar methods that could share
a common superclass.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("extract_superclass_candidates", category="inheritance", severity="medium")
@param("min_shared_methods", int, default=3, description="Minimum shared methods")
@param("limit", int, default=100, description="Maximum results to return")
def extract_superclass_candidates() -> Pipeline:
    """
    Find classes that should share a common superclass.

    Returns:
        findings: List of extract superclass opportunities
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c1 ?class1 ?c2 ?class2 ?file1 ?line1 (COUNT(?shared_name) AS ?shared_methods)
            WHERE {
                ?c1 type {Class} .
                ?c1 name ?class1 .
                ?c1 inFile ?file1 .
                ?c1 atLine ?line1 .
                ?c2 type {Class} .
                ?c2 name ?class2 .
                ?m1 type {Method} .
                ?m1 definedIn ?c1 .
                ?m1 name ?shared_name .
                ?m2 type {Method} .
                ?m2 definedIn ?c2 .
                ?m2 name ?shared_name .
                FILTER ( ?c1 != ?c2 )
                FILTER NOT EXISTS { ?c1 inheritsFrom ?c2 }
                FILTER NOT EXISTS { ?c2 inheritsFrom ?c1 }
            }
            GROUP BY ?c1 ?class1 ?c2 ?class2 ?file1 ?line1
            HAVING (?shared_methods >= {min_shared_methods})
            ORDER BY DESC(?shared_methods)
            LIMIT {limit}
        ''')
        .select("class1", "class2", "file1", "line1", "shared_methods")
        .map(lambda r: {
            **r,
            "file": r.get("file1"),
            "line": r.get("line1"),
            "refactoring": "extract_superclass",
            "message": f"Classes '{r['class1']}' and '{r['class2']}' share {r.get('shared_methods', 0)} methods",
            "suggestion": "Extract a common superclass for shared functionality"
        })
        .emit("findings")
    )

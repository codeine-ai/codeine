"""
replace_conditional_with_polymorphism - Suggest polymorphism over conditionals.

Identifies switch statements or cascading if-else chains that could
be replaced with polymorphism using inheritance or strategy pattern.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("replace_conditional_with_polymorphism", category="refactoring", severity="medium")
@param("min_branches", int, default=4, description="Minimum branches to suggest")
@param("limit", int, default=100, description="Maximum results to return")
def replace_conditional_with_polymorphism() -> Pipeline:
    """
    Suggest Replace Conditional with Polymorphism opportunities.

    Returns:
        findings: List of conditionals that could use polymorphism
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?m ?name ?class_name ?file ?line ?branch_count ?conditional_type
            WHERE {
                ?m type {Method} .
                ?m name ?name .
                ?m inFile ?file .
                ?m atLine ?line .
                OPTIONAL { ?m definedIn ?c . ?c name ?class_name }
                { ?m switchCount ?branch_count  }
                UNION
                { ?m ifElseChainLength ?branch_count                  FILTER ( ?branch_count >= {min_branches} )
            }
            }
            ORDER BY DESC(?branch_count)
        ''')
        .select("name", "class_name", "file", "line", "branch_count", "conditional_type", qualified_name="m")
        .map(lambda r: {
            **r,
            "refactoring": "replace_conditional_with_polymorphism",
            "message": f"Method '{r['name']}' has {r['branch_count']}-branch {r.get('conditional_type', 'conditional')}",
            "suggestion": "Consider using polymorphism (strategy pattern) instead"
        })
        .emit("findings")
    )

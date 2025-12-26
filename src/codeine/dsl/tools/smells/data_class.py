"""
data_class - Detect classes that only hold data without behavior.

Data Classes are classes that have fields and getters/setters but no
real behavior. They may indicate a need for richer domain modeling.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("data_class", category="design", severity="low")
@param("min_attributes", int, default=3, description="Minimum attributes to consider")
@param("max_methods", int, default=2, description="Maximum non-accessor methods")
@param("limit", int, default=100, description="Maximum results to return")
def data_class() -> Pipeline:
    """
    Detect Data Classes - classes with data but no behavior.

    Returns:
        findings: List of potential data classes
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?file ?line (COUNT(?attr) AS ?attr_count) (COUNT(?method) AS ?method_count)
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                OPTIONAL { ?attr type {Field} . ?attr definedIn ?c }
                OPTIONAL { ?method type {Method} . ?method definedIn ?c }
            }
            GROUP BY ?c ?name ?file ?line
            HAVING (?attr_count >= {min_attributes} && ?method_count <= {max_methods})
            ORDER BY DESC(?attr_count)
            LIMIT {limit}
        ''')
        .select("name", "file", "line", "attr_count", "method_count", qualified_name="c")
        .map(lambda r: {
            **r,
            "issue": "data_class",
            "message": f"Class '{r['name']}' has {r.get('attr_count', 0)} attributes but only {r.get('method_count', 0)} methods",
            "suggestion": "Consider adding behavior or using a dataclass/namedtuple"
        })
        .emit("findings")
    )

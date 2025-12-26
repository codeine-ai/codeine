"""
get_class_hierarchy - Get inheritance hierarchy (parents and children).

Returns the complete inheritance tree for a class.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_class_hierarchy")
@param("target", str, required=True, description="Class name to analyze")
def get_class_hierarchy() -> Pipeline:
    """
    Get inheritance hierarchy for a class (parents and children).

    Returns:
        class_name: The target class name
        parents: List of parent class names (direct inheritance)
        children: List of child class names (direct subclasses)
        hierarchy_depth: Depth in inheritance tree
    """
    return (
        reql('''
            SELECT ?c ?name ?qualifiedName ?parent_name ?child_name
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c qualifiedName ?qualifiedName .
                OPTIONAL { ?c inheritsFrom ?parent . ?parent name ?parent_name }
                OPTIONAL { ?child inheritsFrom ?c . ?child name ?child_name }
                FILTER ( ?name = "{target}" || CONTAINS(?qualifiedName, "{target}") )
            }
        ''')
        .select("name", "qualifiedName", "parent_name", "child_name", qualified_name="c")
        .emit("hierarchy")
    )

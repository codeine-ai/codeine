"""
find_subclasses - Find all subclasses of a class (direct and indirect).

Returns the complete list of classes that inherit from the target.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("find_subclasses")
@param("target", str, required=True, description="Class name to find subclasses of")
def find_subclasses() -> Pipeline:
    """
    Find all subclasses of a class (direct and indirect).

    Returns:
        subclasses: List of subclass info with name, file, line
        count: Number of subclasses found
    """
    return (
        reql('''
            SELECT ?sub ?name ?file ?line
            WHERE {
                ?parent type {Class} .
                ?parent name "{target}" .
                ?sub type {Class} .
                ?sub inheritsFrom ?parent .
                ?sub name ?name .
                ?sub inFile ?file .
                ?sub atLine ?line .
            }
        ''')
        .select("name", "file", "line", qualified_name="sub")
        .order_by("file")
        .emit("subclasses")
    )

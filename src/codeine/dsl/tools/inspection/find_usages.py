"""
find_usages - Find where a class/method/function is called in the codebase.

Returns all locations where the target entity is used.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("find_usages")
@param("target", str, required=True, description="Name of class, method, or function to find usages of")
def find_usages() -> Pipeline:
    """
    Find all usages of a class, method, or function.

    Returns:
        usages: List of usage locations with file, line, and context
        count: Number of usages found
    """
    return (
        reql('''
            SELECT ?caller ?caller_name ?caller_file ?caller_line ?call_type
            WHERE {
                { ?caller type {Method} } UNION { ?caller type {Function} }
                ?caller name ?caller_name .
                ?caller inFile ?caller_file .
                ?caller atLine ?caller_line .
                ?caller calls ?target .
                ?target name "{target}".
                            }
        ''')
        .select("caller_name", "caller_file", "caller_line", "call_type", qualified_name="caller")
        .order_by("caller_file")
        .emit("usages")
    )

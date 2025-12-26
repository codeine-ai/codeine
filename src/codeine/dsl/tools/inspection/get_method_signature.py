"""
get_method_signature - Get method signature with parameters and return type.

Returns the full signature information for a method or function.

Reference: d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:658-708
"""

from codeine.dsl import query, param, reql, Pipeline


@query("get_method_signature")
@param("target", str, required=True, description="Method or function name")
def get_method_signature() -> Pipeline:
    """
    Get method signature with parameters and return type.

    Returns:
        signature: Full signature string
        parameters: List of parameter dicts with name, type, default
        return_type: Return type annotation (if present)
        name: Method/function name
        qualifiedName: Fully qualified name
        file: File path
        line: Line number
    """
    return (
        reql('''
            SELECT ?m ?name ?qualifiedName ?file ?line ?return_type ?param_name ?param_type ?param_default
            WHERE {
                { ?m type {Method} } UNION { ?m type {Function} }
                ?m name ?name .
                ?m qualifiedName ?qualifiedName .
                ?m inFile ?file .
                ?m atLine ?line .
                OPTIONAL { ?m returnType ?return_type }
                OPTIONAL {
                    ?m hasParameter ?p .
                    ?p name ?param_name .
                    OPTIONAL { ?p typeAnnotation ?param_type }
                    OPTIONAL { ?p defaultValue ?param_default }
                FILTER ( ?name = "{target}" || CONTAINS(?qualifiedName, "{target}") )
                }
            }
        ''')
        .select("name", "qualifiedName", "file", "line", "return_type", "param_name", "param_type", "param_default", qualified_name="m")
        .emit("signature")
    )

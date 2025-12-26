"""
describe_class - Get detailed description of a class.

Returns class info including methods, attributes, inheritance, and docstring.

Reference: d:/ROOT/codeine/src/codeine/tools/python_basic/python_tools.py:241-500
"""

from codeine.dsl import query, param, reql, Pipeline


@query("describe_class")
@param("target", str, required=True, description="Class name (simple or qualified)")
@param("include_methods", bool, default=True, description="Include method list")
@param("include_attributes", bool, default=True, description="Include attribute list")
@param("include_docstrings", bool, default=True, description="Include docstrings")
def describe_class() -> Pipeline:
    """
    Get detailed description of a class with methods and attributes.

    Returns:
        class_info: Dict with name, qualifiedName, file, line, docstring, parents
        methods: List of method dicts (if include_methods=True)
        attributes: List of attribute dicts (if include_attributes=True)
    """
    return (
        reql('''
            SELECT ?c ?name ?qualifiedName ?file ?line ?docstring ?parent_name
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c qualifiedName ?qualifiedName .
                ?c inFile ?file .
                ?c atLine ?line .
                OPTIONAL { ?c docstring ?docstring }
                OPTIONAL { ?c inheritsFrom ?parent . ?parent name ?parent_name }
                FILTER ( CONTAINS(?qualifiedName, "{target}") || ?name = "{target}" )
            }
        ''')
        .select(
            "name", "qualifiedName", "file", "line", "docstring",
            parent="parent_name",
            qualified_name="c"
        )
        .emit("class_info")
    )

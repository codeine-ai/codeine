"""
predict_impact - Predict impact of changing a function/method/class.

Analyzes the dependency graph to predict which files and entities
would be affected by changes to the target.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("predict_impact")
@param("target", str, required=True, description="Entity name to analyze impact for")
def predict_impact() -> Pipeline:
    """
    Predict impact of changing a function/method/class.

    Returns:
        affected_files: List of files that would be affected
        affected_entities: List of entities that depend on target
        risk_level: Estimated risk level (low, medium, high)
    """
    return (
        reql('''
            SELECT ?dependent ?dep_name ?dep_file ?dep_line ?dep_type
            WHERE {
                ?target name "{target}".
                { ?target type {Class} } UNION { ?target type {Method} } UNION { ?target type {Function} }
                { ?dependent type {Class} } UNION { ?dependent type {Method} } UNION { ?dependent type {Function} }
                { ?dependent callsTransitive ?target } UNION { ?dependent inheritsFrom ?target } UNION { ?dependent imports ?target }
                ?dependent name ?dep_name .
                ?dependent inFile ?dep_file .
                ?dependent atLine ?dep_line .
                
                
                
            }
        ''')
        .select("dep_name", "dep_file", "dep_line", "dep_type", qualified_name="dependent")
        .order_by("dep_file")
        .emit("affected_entities")
    )

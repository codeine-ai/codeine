"""
pipeline_conversion - Detect loops that could be replaced with collection pipelines.

Loops that filter, transform, or aggregate collections can often be
expressed more clearly using map/filter/reduce operations.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("pipeline_conversion", category="refactoring", severity="low")
@param("limit", int, default=100, description="Maximum results to return")
def pipeline_conversion() -> Pipeline:
    """
    Detect loops replaceable with collection pipeline operations.

    Returns:
        findings: List of loops suitable for pipeline conversion
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?loop ?func_name ?file ?line ?pattern ?collection ?suggested_pipeline
            WHERE {
                ?loop type {Loop} .
                ?loop inFunction ?func .
                ?func name ?func_name .
                ?loop inFile ?file .
                ?loop atLine ?line .
                ?loop pipelinePattern ?pattern .
                ?loop iteratedCollection ?collection .
                ?loop suggestedPipeline ?suggested_pipeline .
                FILTER ( ?pattern != "none" )
            }
            ORDER BY ?file ?line
            LIMIT {limit}
        ''')
        .select("func_name", "file", "line", "pattern", "collection", "suggested_pipeline")
        .map(lambda r: {
            **r,
            "refactoring": "replace_loop_with_pipeline",
            "message": f"Loop in '{r['func_name']}' follows '{r['pattern']}' pattern",
            "suggestion": f"Replace with: {r.get('suggested_pipeline', 'list comprehension or generator')}"
        })
        .emit("findings")
    )

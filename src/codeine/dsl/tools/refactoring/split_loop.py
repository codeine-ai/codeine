"""
split_loop - Detect loops doing multiple independent things.

A loop that does multiple unrelated operations should be split into
separate loops for clarity and potential optimization.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("split_loop", category="refactoring", severity="low")
@param("min_operations", int, default=2, description="Minimum independent operations")
@param("limit", int, default=100, description="Maximum results to return")
def split_loop() -> Pipeline:
    """
    Detect loops performing multiple independent operations.

    Returns:
        findings: List of loops that should be split
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?loop ?func_name ?file ?line ?operation_count ?operations ?loop_type
            WHERE {
                ?loop type {Loop} .
                ?loop inFunction ?func .
                ?func name ?func_name .
                ?loop inFile ?file .
                ?loop atLine ?line .
                ?loop independentOperationCount ?operation_count .
                ?loop operations ?operations .
                ?loop loopType ?loop_type .
            FILTER ( ?operation_count >= {min_operations} )
            }
            ORDER BY DESC(?operation_count)
            LIMIT {limit}
        ''')
        .select("func_name", "file", "line", "operation_count", "operations", "loop_type")
        .map(lambda r: {
            **r,
            "refactoring": "split_loop",
            "message": f"{r['loop_type']} loop in '{r['func_name']}' does {r['operation_count']} independent operations",
            "suggestion": "Split into separate loops, each doing one thing"
        })
        .emit("findings")
    )

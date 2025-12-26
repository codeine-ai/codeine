"""
find_decorator_usage - Find all decorator usages in the codebase.

Identifies all decorators used on classes, methods, and functions.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_decorator_usage", category="patterns", severity="info")
@param("decorator_name", str, required=False, default=None, description="Filter by decorator name")
@param("limit", int, default=100, description="Maximum results to return")
def find_decorator_usage() -> Pipeline:
    """
    Find all decorator usages in the codebase.

    Returns:
        findings: List of decorator usages
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?d ?decorator_name ?target_name ?target_type ?file ?line
            WHERE {
                { ?target type {Class}  }
                UNION
                { ?target type {Method}  }
                UNION
                { ?target type {Function}  }
                ?target hasDecorator ?d .
                ?d name ?decorator_name .
                ?target name ?target_name .
                ?target inFile ?file .
                ?target atLine ?line
            }
            ORDER BY ?decorator_name ?file
        ''')
        .select("decorator_name", "target_name", "target_type", "file", "line")
        .emit("findings")
    )

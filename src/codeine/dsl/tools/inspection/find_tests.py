"""
find_tests - Find test classes/functions for a module, class, or function.

Returns test coverage information for the specified target.
"""

from codeine.dsl import query, param, reql, Pipeline


@query("find_tests")
@param("target", str, required=False, default=None, description="Name of module, class, or function to find tests for")
@param("module", str, required=False, default=None, description="Module name filter")
def find_tests() -> Pipeline:
    """
    Find test classes/functions for a module, class, or function.

    Returns:
        tests_found: List of test functions/classes found
        suggestions: Suggested test locations if no tests found
    """
    return (
        reql('''
            SELECT ?t ?test_name ?test_type ?file ?line
            WHERE {
                { ?t type {Class}  }
                UNION
                { ?t type {Function}  }
                ?t name ?test_name .
                ?t inFile ?file .
                ?t atLine ?line .
                FILTER ( REGEX(?test_name, "^test_|^Test|_test$") )
            }
            ORDER BY ?file ?line
        ''')
        .select("test_name", "test_type", "file", "line", qualified_name="t")
        .emit("tests_found")
    )

"""
find_factory_pattern - Find classes/methods implementing factory pattern.

Identifies factory methods and factory classes.
"""

from codeine.dsl import detector, param, reql, Pipeline


@detector("find_factory_pattern", category="patterns", severity="info")
@param("limit", int, default=100, description="Maximum results to return")
def find_factory_pattern() -> Pipeline:
    """
    Find factory pattern implementations.

    Returns:
        findings: List of factory implementations
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?e ?name ?entity_type ?file ?line ?creates_type
            WHERE {
                {
                    ?e type {Method} .
                    ?e isFactoryMethod true.
                                    }
                UNION
                {
                    ?e type {Class} .
                    ?e isFactoryClass true.
                                    }
                ?e name ?name .
                ?e inFile ?file .
                ?e atLine ?line .
                OPTIONAL { ?e createsType ?creates_type }
            }
            ORDER BY ?entity_type ?name
        ''')
        .select("name", "entity_type", "file", "line", "creates_type")
        .emit("findings")
    )

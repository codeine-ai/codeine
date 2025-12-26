"""
duplicate_names - Detect entities with duplicate names across modules.

Having multiple classes, functions, or variables with the same name
in different modules can lead to confusion and import conflicts.

Uses Python grouping to find names appearing in multiple files.
"""

from typing import Dict, List, Set
from collections import defaultdict
from codeine.dsl import detector, param, reql, Pipeline


@detector("duplicate_names", category="code_smell", severity="low")
@param("entity_type", str, default="class", description="Entity type: class, function, or all")
@param("limit", int, default=100, description="Maximum results to return")
def duplicate_names() -> Pipeline:
    """
    Detect duplicate entity names across different modules.

    Returns:
        findings: List of duplicate name occurrences
        count: Number of findings
    """
    # Query all entities and add type marker in Python processing
    return (
        reql('''
            SELECT ?name ?file ?concept
            WHERE {
                ?e type {Class} .
                ?e name ?name .
                ?e inFile ?file .
                ?e concept ?concept .
            }
        ''')
        .tap(_find_duplicates)
        .emit("findings")
    )


def _find_duplicates(rows: List[Dict], ctx=None) -> List[Dict]:
    """
    Group entities by name and find duplicates using Python.
    """
    # Get parameters from context
    entity_type = "class"
    limit = 100
    if ctx is not None:
        entity_type = ctx.params.get('entity_type', 'class')
        limit = ctx.params.get('limit', 100)

    # Group by name
    name_occurrences: Dict[str, Dict] = defaultdict(lambda: {
        "files": set(),
        "types": set()
    })

    for row in rows:
        name = row.get('name')
        file = row.get('file')
        # Derive type from concept (e.g., "oo:Class" -> "class")
        concept = row.get('concept', '')
        etype = concept.split(':')[-1].lower() if ':' in concept else concept.lower()

        if not name or not file:
            continue

        # Filter by entity type
        if entity_type != "all" and etype != entity_type:
            continue

        name_occurrences[name]["files"].add(file)
        name_occurrences[name]["types"].add(etype)

    # Find duplicates (names appearing in multiple files)
    findings = []
    for name, data in name_occurrences.items():
        if len(data["files"]) > 1:
            findings.append({
                "name": name,
                "count": len(data["files"]),
                "files": list(data["files"])[:5],  # Limit shown files
                "types": list(data["types"]),
                "issue": "duplicate_name",
                "message": f"Name '{name}' appears {len(data['files'])} times in different modules",
                "suggestion": "Consider using more specific names or reorganizing into a single location"
            })

    # Sort by count descending
    findings.sort(key=lambda x: x["count"], reverse=True)
    return findings[:limit]

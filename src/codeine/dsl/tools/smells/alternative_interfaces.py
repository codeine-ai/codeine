"""
alternative_interfaces - Detect classes with similar responsibilities but different interfaces.

These are classes that do similar things but have different method signatures,
making it harder to use them interchangeably.

Uses Python N² comparison to calculate method similarity between class pairs.
"""

from typing import Dict, List, Set, Tuple
from codeine.dsl import detector, param, reql, Pipeline


@detector("alternative_interfaces", category="code_smell", severity="medium")
@param("min_similarity", float, default=0.6, description="Minimum method similarity threshold")
@param("min_shared_methods", int, default=3, description="Minimum shared methods to report")
@param("limit", int, default=100, description="Maximum results to return")
def alternative_interfaces() -> Pipeline:
    """
    Detect classes with similar behavior but different interfaces.

    Queries all classes with their methods, then uses Python N² comparison
    to find classes with similar method sets but different interfaces.

    Returns:
        findings: List of class pairs with similar functionality but different APIs
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?class_name ?method_name ?file ?line
            WHERE {
                ?c type {Class} .
                ?c name ?class_name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?m type {Method} .
                ?m definedIn ?c .
                ?m name ?method_name .
                FILTER ( !STRSTARTS(?method_name, "_") )
            }
        ''')
        .select("c", "class_name", "method_name", "file", "line")
        .tap(_find_similar_interfaces)
        .emit("findings")
    )


def _find_similar_interfaces(rows: List[Dict], ctx=None) -> List[Dict]:
    """
    Find classes with similar method sets using N² comparison.

    Uses Jaccard similarity: |intersection| / |union|
    """
    # Get parameters from context
    min_similarity = 0.6
    min_shared_methods = 3
    limit = 100
    if ctx is not None:
        min_similarity = ctx.params.get('min_similarity', 0.6)
        min_shared_methods = ctx.params.get('min_shared_methods', 3)
        limit = ctx.params.get('limit', 100)

    # Build class -> methods mapping
    class_methods: Dict[str, Dict] = {}

    for row in rows:
        class_id = row.get('c')
        class_name = row.get('class_name')
        method_name = row.get('method_name')
        file = row.get('file')
        line = row.get('line')

        if class_id and class_name and method_name:
            if class_id not in class_methods:
                class_methods[class_id] = {
                    "name": class_name,
                    "file": file,
                    "line": line,
                    "methods": set()
                }
            class_methods[class_id]["methods"].add(method_name)

    # N² comparison to find similar classes
    findings = []
    class_list = list(class_methods.items())
    seen_pairs: Set[Tuple[str, str]] = set()

    for i, (class_id1, data1) in enumerate(class_list):
        for j in range(i + 1, len(class_list)):
            class_id2, data2 = class_list[j]

            methods1 = data1["methods"]
            methods2 = data2["methods"]

            # Skip classes with too few methods
            if len(methods1) < 2 or len(methods2) < 2:
                continue

            # Calculate Jaccard similarity
            intersection = methods1 & methods2
            union = methods1 | methods2
            shared_count = len(intersection)
            different_count = len(union) - shared_count

            if len(union) == 0:
                continue

            similarity = shared_count / len(union)

            # Check thresholds
            if similarity >= min_similarity and shared_count >= min_shared_methods and different_count > 0:
                # Normalize pair for deduplication
                pair = tuple(sorted([data1["name"], data2["name"]]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    findings.append({
                        "name1": data1["name"],
                        "name2": data2["name"],
                        "file": data1["file"],
                        "line": data1["line"],
                        "similarity": round(similarity, 2),
                        "shared_methods": shared_count,
                        "different_methods": different_count,
                        "shared_method_names": list(intersection)[:5],
                        "issue": "alternative_interfaces",
                        "message": f"Classes '{data1['name']}' and '{data2['name']}' are {int(similarity*100)}% similar but have {different_count} different methods",
                        "suggestion": "Consider extracting a common interface or unifying method signatures"
                    })

    # Sort by similarity descending and apply limit
    findings.sort(key=lambda x: x["similarity"], reverse=True)
    return findings[:limit]

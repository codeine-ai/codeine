"""
parallel_inheritance - Detect parallel inheritance hierarchies.

Parallel inheritance occurs when you have to create a subclass of one class
every time you create a subclass of another class. This is detected by
finding classes with matching naming patterns (e.g., FooA/BarA and FooB/BarB).

Uses Python post-processing to analyze class naming patterns.
"""

from typing import Dict, List, Set, Tuple
from collections import defaultdict
from codeine.dsl import detector, param, reql, Pipeline


@detector("parallel_inheritance", category="code_smell", severity="medium")
@param("min_parallel_pairs", int, default=2, description="Minimum parallel class pairs")
@param("limit", int, default=100, description="Maximum results to return")
def parallel_inheritance() -> Pipeline:
    """
    Detect parallel inheritance hierarchies - mirrored class structures.

    Analyzes class naming patterns to find parallel hierarchies where
    different groups of classes follow similar naming conventions.

    Returns:
        findings: List of parallel hierarchy pairs
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?c ?name ?base_name ?file ?line
            WHERE {
                ?c type {Class} .
                ?c name ?name .
                ?c inFile ?file .
                ?c atLine ?line .
                ?c inheritsFrom ?base .
                ?base name ?base_name .
            }
        ''')
        .select("c", "name", "base_name", "file", "line")
        .tap(_find_parallel_hierarchies)
        .emit("findings")
    )


def _find_parallel_hierarchies(rows: List[Dict], ctx=None) -> List[Dict]:
    """
    Find parallel hierarchies by analyzing naming patterns.

    Groups subclasses by their base class, then looks for
    classes with matching prefixes or suffixes that suggest
    parallel implementation patterns.
    """
    # Get parameters from context
    min_parallel_pairs = 2
    limit = 100
    if ctx is not None:
        min_parallel_pairs = ctx.params.get('min_parallel_pairs', 2)
        limit = ctx.params.get('limit', 100)

    # Group classes by base class
    by_base: Dict[str, List[Dict]] = defaultdict(list)

    for row in rows:
        base = row.get('base_name')
        name = row.get('name')
        if base and name:
            by_base[base].append({
                "name": name,
                "file": row.get('file'),
                "line": row.get('line')
            })

    findings = []
    seen_pairs: Set[Tuple[str, str]] = set()

    # Look for parallel patterns across different base classes
    base_list = list(by_base.items())

    for i, (base1, children1) in enumerate(base_list):
        for j in range(i + 1, len(base_list)):
            base2, children2 = base_list[j]

            # Find matching name patterns between the two hierarchies
            parallel_pairs = _find_parallel_pairs(children1, children2)

            if len(parallel_pairs) >= min_parallel_pairs:
                # Normalize pair for deduplication
                pair = tuple(sorted([base1, base2]))
                if pair not in seen_pairs:
                    seen_pairs.add(pair)

                    # Use first child's file/line for location
                    first_child = children1[0] if children1 else {}

                    findings.append({
                        "base1": base1,
                        "base2": base2,
                        "parallel_pairs": len(parallel_pairs),
                        "examples": parallel_pairs[:3],
                        "file": first_child.get("file", ""),
                        "line": first_child.get("line", 0),
                        "issue": "parallel_inheritance",
                        "message": f"Hierarchies under '{base1}' and '{base2}' have {len(parallel_pairs)} parallel pairs",
                        "suggestion": "Consider merging hierarchies or using composition instead of inheritance"
                    })

    # Sort by number of parallel pairs
    findings.sort(key=lambda x: x["parallel_pairs"], reverse=True)
    return findings[:limit]


def _find_parallel_pairs(children1: List[Dict], children2: List[Dict]) -> List[Tuple[str, str]]:
    """
    Find matching pairs of classes between two hierarchies.

    Looks for classes with matching prefixes/suffixes (e.g., FooHandler/BarHandler).
    """
    names1 = {c["name"] for c in children1}
    names2 = {c["name"] for c in children2}

    pairs = []

    for n1 in names1:
        for n2 in names2:
            if _names_are_parallel(n1, n2):
                pairs.append((n1, n2))

    return pairs


def _names_are_parallel(name1: str, name2: str) -> bool:
    """
    Check if two class names suggest parallel implementation.

    Returns True if names share a common prefix or suffix
    that suggests they implement similar functionality.
    """
    if name1 == name2:
        return False

    # Must be at least 3 chars to have meaningful prefix/suffix
    if len(name1) < 3 or len(name2) < 3:
        return False

    # Check for common suffix (e.g., FooHandler, BarHandler)
    min_len = min(len(name1), len(name2))
    for suffix_len in range(3, min_len):
        if name1[-suffix_len:] == name2[-suffix_len:]:
            # Ensure prefix differs meaningfully
            prefix1 = name1[:-suffix_len]
            prefix2 = name2[:-suffix_len]
            if prefix1 and prefix2 and prefix1 != prefix2:
                return True

    # Check for common prefix (e.g., AbstractFoo, AbstractBar)
    for prefix_len in range(3, min_len):
        if name1[:prefix_len] == name2[:prefix_len]:
            # Ensure suffix differs meaningfully
            suffix1 = name1[prefix_len:]
            suffix2 = name2[prefix_len:]
            if suffix1 and suffix2 and suffix1 != suffix2:
                return True

    return False

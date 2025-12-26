"""
find_circular_imports - Find circular import dependencies.

Identifies modules that have circular import relationships using DFS
cycle detection on the import graph.
"""

from typing import Dict, List, Set, Tuple
from codeine.dsl import detector, param, reql, Pipeline


@detector("find_circular_imports", category="dependencies", severity="high")
@param("limit", int, default=100, description="Maximum results to return")
def find_circular_imports() -> Pipeline:
    """
    Find circular import dependencies.

    Queries all import relationships and uses DFS to detect cycles
    in the import graph.

    Returns:
        findings: List of circular import chains
        count: Number of findings
    """
    return (
        reql('''
            SELECT ?module1 ?module2 ?file1 ?file2
            WHERE {
                ?m1 type {Module} .
                ?m1 name ?module1 .
                ?m1 inFile ?file1 .
                ?m1 imports ?m2 .
                ?m2 type {Module} .
                ?m2 name ?module2 .
                ?m2 inFile ?file2 .
            }
        ''')
        .select("module1", "module2", "file1", "file2")
        .tap(lambda rows: _detect_circular_imports(rows))
        .emit("findings")
    )


def _detect_circular_imports(rows: List[Dict]) -> List[Dict]:
    """
    Detect circular imports using DFS cycle detection.

    Builds an adjacency graph from import relationships and uses DFS
    with a recursion stack to find all cycles.
    """
    # Build adjacency graph and file mapping
    graph: Dict[str, List[str]] = {}
    file_map: Dict[str, str] = {}

    for row in rows:
        module1 = row.get('module1')
        module2 = row.get('module2')
        file1 = row.get('file1')
        file2 = row.get('file2')

        if module1 and module2:
            if module1 not in graph:
                graph[module1] = []
            graph[module1].append(module2)

            if file1:
                file_map[module1] = file1
            if file2:
                file_map[module2] = file2

    # Find cycles using DFS
    cycles = _detect_cycles_dfs(graph)

    # Convert cycles to findings
    findings = []
    seen_pairs: Set[Tuple[str, str]] = set()

    for cycle in cycles:
        if len(cycle) >= 2:
            # For each cycle, report the first pair (to avoid duplicates)
            # Normalize pair order for deduplication
            for i in range(len(cycle) - 1):
                m1, m2 = cycle[i], cycle[i + 1]
                pair = tuple(sorted([m1, m2]))

                if pair not in seen_pairs:
                    seen_pairs.add(pair)
                    findings.append({
                        "module1": m1,
                        "module2": m2,
                        "file1": file_map.get(m1, ""),
                        "file2": file_map.get(m2, ""),
                        "cycle": cycle,
                        "cycle_length": len(cycle) - 1,
                        "issue": "circular_import",
                        "message": f"Circular import between '{m1}' and '{m2}' (cycle length: {len(cycle) - 1})",
                        "suggestion": "Break the cycle by moving shared code to a separate module or using lazy imports"
                    })

    return findings


def _detect_cycles_dfs(graph: Dict[str, List[str]]) -> List[List[str]]:
    """
    Detect all cycles in a directed graph using DFS.

    Uses a recursion stack to detect back edges that indicate cycles.
    """
    seen_cycles: Set[Tuple[str, ...]] = set()
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def dfs(node: str, path: List[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, path)
            elif neighbor in rec_stack:
                # Found a cycle - extract it
                if neighbor in path:
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    normalized = _normalize_cycle(cycle)
                    if normalized not in seen_cycles:
                        seen_cycles.add(normalized)
                        cycles.append(list(cycle))

        path.pop()
        rec_stack.remove(node)

    for node in graph:
        if node not in visited:
            dfs(node, [])

    return cycles


def _normalize_cycle(cycle: List[str]) -> Tuple[str, ...]:
    """
    Normalize a cycle for deduplication.

    Rotates the cycle to start with the lexicographically smallest element,
    ensuring the same cycle detected from different starting points
    is recognized as identical.
    """
    if len(cycle) <= 1:
        return tuple(cycle)

    # Remove the duplicate last element (cycle closes back to start)
    unique = cycle[:-1] if cycle[0] == cycle[-1] else cycle

    if not unique:
        return tuple(cycle)

    # Find the minimum element and rotate to start there
    min_idx = unique.index(min(unique))
    rotated = unique[min_idx:] + unique[:min_idx]

    return tuple(rotated)

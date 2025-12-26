"""
detect_extraction_opportunities - Find similar code blocks for extraction.

Uses the RAG manager to find semantically similar code that can be
extracted into shared functions, with scope filtering and extraction analysis.
"""

from typing import Dict, Any, List, Optional
from codeine.dsl import detector, param, Pipeline
from codeine.dsl.core import Source, Context, PipelineResult, pipeline_ok, pipeline_err


class ExtractionOpportunitiesSource(Source[List[Dict[str, Any]]]):
    """Source that finds extraction opportunities via RAG similarity search."""

    def __init__(
        self,
        similarity_threshold: float = 0.80,
        scope: str = "same_class",  # "same_class", "same_module", "any"
        min_lines: int = 3,
        max_results: int = 20,
        entity_types: Optional[List[str]] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.scope = scope
        self.min_lines = min_lines
        self.max_results = max_results
        self.entity_types = entity_types or ["method", "function"]

    def execute(self, ctx: Context) -> PipelineResult[List[Dict[str, Any]]]:
        """Execute extraction opportunity detection via RAG manager."""
        try:
            # Get RAG manager from context or default instance manager
            rag_manager = ctx.get("rag_manager")
            if rag_manager is None:
                # Try to get from default instance manager
                from codeine.services.default_instance_manager import DefaultInstanceManager
                default_mgr = DefaultInstanceManager.get_instance()
                if default_mgr:
                    rag_manager = default_mgr.get_rag_manager()

            if rag_manager is None:
                return pipeline_err(
                    "rag",
                    "RAG manager not available. Ensure RAG is enabled and initialized.",
                    None
                )

            # Use slightly lower threshold to catch more candidates
            rag_threshold = max(0.70, self.similarity_threshold - 0.10)

            # Get similar code pairs from RAG
            result = rag_manager.find_duplicate_candidates(
                similarity_threshold=rag_threshold,
                max_results=self.max_results * 3,  # Get more, will filter
                exclude_same_file=False,  # We want same-file matches for extraction
                exclude_same_class=False,  # We want same-class matches
                entity_types=self.entity_types
            )

            if not result.get("success"):
                return pipeline_err("rag", result.get("error", "RAG search failed"), None)

            pairs = result.get("pairs", [])
            if not pairs:
                return pipeline_ok([])

            # Filter by scope
            filtered = []
            for pair in pairs:
                e1 = pair["entity1"]
                e2 = pair["entity2"]

                # Skip if same entity
                if e1["file"] == e2["file"] and e1["line"] == e2["line"]:
                    continue

                # Skip if below threshold after filtering
                if pair["similarity"] < self.similarity_threshold:
                    continue

                # Apply scope filter
                if self.scope == "same_class":
                    c1 = e1.get("class_name", "")
                    c2 = e2.get("class_name", "")
                    if not c1 or not c2 or c1 != c2:
                        continue
                    if e1["file"] != e2["file"]:
                        continue
                elif self.scope == "same_module":
                    if e1["file"] != e2["file"]:
                        continue
                # scope == "any" - no filtering

                filtered.append({
                    "similarity": pair["similarity"],
                    "entity1_name": e1["name"],
                    "entity1_file": e1["file"],
                    "entity1_line": e1["line"],
                    "entity1_class": e1.get("class_name", ""),
                    "entity2_name": e2["name"],
                    "entity2_file": e2["file"],
                    "entity2_line": e2["line"],
                    "entity2_class": e2.get("class_name", ""),
                    "scope": self.scope,
                    "in_same_file": e1["file"] == e2["file"],
                    "in_same_class": e1.get("class_name") == e2.get("class_name") and e1.get("class_name"),
                })

            return pipeline_ok(filtered[:self.max_results])

        except Exception as e:
            return pipeline_err("rag", f"Extraction opportunity detection failed: {e}", e)


@detector("detect_extraction_opportunities", category="refactoring", severity="high")
@param("similarity_threshold", float, default=0.80, description="Minimum similarity (0-1)")
@param("scope", str, default="same_class", description="Scope: same_class, same_module, any")
@param("min_lines", int, default=3, description="Minimum lines in code blocks")
@param("max_results", int, default=20, description="Maximum opportunities to return")
def detect_extraction_opportunities() -> Pipeline:
    """
    Find similar code blocks that can be extracted into shared functions.

    Uses RAG semantic similarity to find code pairs that are good candidates
    for extraction. Filters by scope (same class, same module, or any) and
    analyzes the similarity to determine extraction potential.

    Returns:
        findings: List of extraction opportunities with details
        count: Number of opportunities found
    """
    return (
        Pipeline.from_source(ExtractionOpportunitiesSource(
            similarity_threshold=0.80,
            scope="same_class",
            min_lines=3,
            max_results=20,
            entity_types=["method", "function"]
        ))
        .map(lambda r: {
            **r,
            "issue": "extraction_opportunity",
            "message": f"'{r['entity1_name']}' and '{r['entity2_name']}' are {int(r['similarity'] * 100)}% similar" +
                      (f" in class '{r['entity1_class']}'" if r.get('in_same_class') else ""),
            "suggestion": "Extract common logic into a shared private method",
            "refactoring": "Extract Function (106)"
        })
        .emit("findings")
    )

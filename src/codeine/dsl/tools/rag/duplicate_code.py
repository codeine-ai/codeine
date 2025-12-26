"""
detect_duplicate_code - Find semantically similar code pairs using RAG embeddings.

Uses the RAG index manager to find code entities that are highly similar,
indicating potential code duplication that could be refactored.
"""

from typing import Dict, Any, List, Optional
from codeine.dsl import detector, param, Pipeline
from codeine.dsl.core import Source, Context, PipelineResult, pipeline_ok, pipeline_err


class DuplicateCodeSource(Source[List[Dict[str, Any]]]):
    """Source that calls RAG manager's find_duplicate_candidates method."""

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_results: int = 50,
        exclude_same_file: bool = True,
        exclude_same_class: bool = True,
        entity_types: Optional[List[str]] = None
    ):
        self.similarity_threshold = similarity_threshold
        self.max_results = max_results
        self.exclude_same_file = exclude_same_file
        self.exclude_same_class = exclude_same_class
        self.entity_types = entity_types or ["method", "function"]

    def execute(self, ctx: Context) -> PipelineResult[List[Dict[str, Any]]]:
        """Execute duplicate detection via RAG manager."""
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

            # Call the actual RAG manager method
            result = rag_manager.find_duplicate_candidates(
                similarity_threshold=self.similarity_threshold,
                max_results=self.max_results,
                exclude_same_file=self.exclude_same_file,
                exclude_same_class=self.exclude_same_class,
                entity_types=self.entity_types
            )

            if not result.get("success"):
                return pipeline_err("rag", result.get("error", "Duplicate detection failed"), None)

            # Transform pairs to findings format
            findings = []
            for pair in result.get("pairs", []):
                e1 = pair["entity1"]
                e2 = pair["entity2"]
                findings.append({
                    "similarity": pair["similarity"],
                    "entity1_name": e1["name"],
                    "entity1_file": e1["file"],
                    "entity1_line": e1["line"],
                    "entity1_class": e1.get("class_name", ""),
                    "entity2_name": e2["name"],
                    "entity2_file": e2["file"],
                    "entity2_line": e2["line"],
                    "entity2_class": e2.get("class_name", ""),
                    "entity1": e1,
                    "entity2": e2
                })

            return pipeline_ok(findings)

        except Exception as e:
            return pipeline_err("rag", f"Duplicate code search failed: {e}", e)


@detector("detect_duplicate_code", category="duplication", severity="high")
@param("similarity_threshold", float, default=0.85, description="Minimum similarity (0-1)")
@param("max_results", int, default=50, description="Maximum pairs to return")
@param("exclude_same_file", bool, default=True, description="Exclude same-file matches")
@param("exclude_same_class", bool, default=True, description="Exclude same-class matches")
def detect_duplicate_code() -> Pipeline:
    """
    Find semantically similar code pairs using RAG embeddings.

    Uses vector similarity to identify code that may be duplicated
    across different files or classes, indicating refactoring opportunities.

    Returns:
        findings: List of similar code pairs with similarity scores
        count: Number of duplicate pairs found
    """
    return (
        Pipeline.from_source(DuplicateCodeSource(
            similarity_threshold=0.85,
            max_results=50,
            exclude_same_file=True,
            exclude_same_class=True,
            entity_types=["method", "function"]
        ))
        .map(lambda r: {
            **r,
            "issue": "duplicate_code",
            "message": f"'{r['entity1_name']}' and '{r['entity2_name']}' are {int(r['similarity'] * 100)}% similar",
            "suggestion": f"Consider extracting common logic into a shared function or using delegation pattern",
            "refactoring": "Extract Function (106) or Replace Superclass with Delegate (399)"
        })
        .emit("findings")
    )

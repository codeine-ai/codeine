"""
find_similar_clusters - Find clusters of semantically similar code using K-means.

Uses the RAG index manager to perform K-means clustering on code embeddings,
grouping similar code patterns that may indicate duplication opportunities.
"""

from typing import Dict, Any, List, Optional
from codeine.dsl import detector, param, Pipeline
from codeine.dsl.core import Source, Context, PipelineResult, pipeline_ok, pipeline_err


class SimilarClustersSource(Source[List[Dict[str, Any]]]):
    """Source that calls RAG manager's find_similar_clusters method."""

    def __init__(
        self,
        n_clusters: int = 50,
        min_cluster_size: int = 2,
        exclude_same_file: bool = True,
        exclude_same_class: bool = True,
        entity_types: Optional[List[str]] = None
    ):
        self.n_clusters = n_clusters
        self.min_cluster_size = min_cluster_size
        self.exclude_same_file = exclude_same_file
        self.exclude_same_class = exclude_same_class
        self.entity_types = entity_types or ["method", "function"]

    def execute(self, ctx: Context) -> PipelineResult[List[Dict[str, Any]]]:
        """Execute K-means clustering via RAG manager."""
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
            result = rag_manager.find_similar_clusters(
                n_clusters=self.n_clusters,
                min_cluster_size=self.min_cluster_size,
                exclude_same_file=self.exclude_same_file,
                exclude_same_class=self.exclude_same_class,
                entity_types=self.entity_types
            )

            if not result.get("success"):
                return pipeline_err("rag", result.get("error", "Clustering failed"), None)

            # Transform clusters to findings format
            findings = []
            for cluster in result.get("clusters", []):
                member_names = [m["name"] for m in cluster["members"]]
                member_files = list(set(m["file"] for m in cluster["members"]))
                findings.append({
                    "cluster_id": cluster["cluster_id"],
                    "member_count": cluster["member_count"],
                    "unique_files": cluster["unique_files"],
                    "members": member_names,
                    "files": member_files,
                    "avg_distance": cluster.get("avg_distance", 0),
                    "details": cluster["members"]  # Full member details
                })

            return pipeline_ok(findings)

        except Exception as e:
            return pipeline_err("rag", f"Similar clusters search failed: {e}", e)


@detector("find_similar_clusters", category="duplication", severity="medium")
@param("n_clusters", int, default=50, description="Number of K-means clusters")
@param("min_cluster_size", int, default=2, description="Minimum items per cluster")
@param("exclude_same_file", bool, default=True, description="Exclude same-file matches")
@param("exclude_same_class", bool, default=True, description="Exclude same-class matches")
@param("limit", int, default=100, description="Maximum results to return")
def find_similar_clusters() -> Pipeline:
    """
    Find clusters of semantically similar code using K-means clustering.

    Uses RAG embeddings to group code by semantic similarity. Clusters with
    multiple members from different files/classes indicate potential
    duplication or extraction opportunities.

    Returns:
        findings: List of code clusters with member details
        count: Number of clusters found
    """
    return (
        Pipeline.from_source(SimilarClustersSource(
            n_clusters=50,  # Will be overridden by params at runtime
            min_cluster_size=2,
            exclude_same_file=True,
            exclude_same_class=True,
            entity_types=["method", "function"]
        ))
        .map(lambda r: {
            **r,
            "issue": "similar_cluster",
            "message": f"Cluster of {r['member_count']} similar code blocks across {r['unique_files']} files: {', '.join(r['members'][:3])}{'...' if len(r['members']) > 3 else ''}",
            "suggestion": "Review cluster for potential abstraction - Extract Function (106) or Pull Up Method (350)",
            "refactoring": "extract_function"
        })
        .emit("findings")
    )

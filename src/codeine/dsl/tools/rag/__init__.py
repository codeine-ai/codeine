"""
RAG-based Semantic Detectors - Use embeddings for semantic code analysis.

All tools in this package use the RAG index manager for semantic similarity:
- detect_duplicate_code: Find semantically similar code pairs
- find_similar_clusters: K-means clustering of similar code
- detect_extraction_opportunities: Find code blocks for extraction

These tools require the RAG index to be initialized and available.
"""

from .duplicate_code import detect_duplicate_code
from .similar_clusters import find_similar_clusters
from .extraction_opportunities import detect_extraction_opportunities

__all__ = [
    "detect_duplicate_code",
    "find_similar_clusters",
    "detect_extraction_opportunities",
]

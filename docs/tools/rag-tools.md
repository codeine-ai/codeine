# RAG Tools

Retrieval-Augmented Generation tools for semantic search and code analysis.

## Overview

Codeine's RAG system uses FAISS vector indexes with sentence-transformers embeddings to enable semantic search across code and documentation.

## Tools

### semantic_search

Search code and documentation using natural language.

```python
semantic_search(
    query="authentication and JWT tokens",
    top_k=10,
    search_scope="all"
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | required | Natural language search query |
| `top_k` | int | 10 | Maximum results |
| `entity_types` | list | None | Filter: class, method, function, section, document, code_block |
| `file_filter` | str | None | Glob pattern (e.g., "src/**/*.py") |
| `include_content` | bool | False | Include source code in results |
| `search_scope` | str | "all" | Scope: all, code, docs |
| `instance_name` | str | "default" | RETER instance name |

#### Returns

```python
{
    "success": True,
    "results": [
        {
            "entity_type": "method",
            "name": "authenticate_user",
            "qualified_name": "auth.service.AuthService.authenticate_user",
            "file": "src/auth/service.py",
            "line": 45,
            "end_line": 78,
            "score": 0.92,
            "source_type": "python",
            "docstring": "Authenticate a user with credentials..."
        }
    ],
    "count": 10,
    "query_embedding_time_ms": 12,
    "search_time_ms": 3,
    "total_vectors": 1523
}
```

#### Examples

```python
# Search code only
semantic_search("error handling", search_scope="code")

# Search specific entity types
semantic_search("database connection", entity_types=["class", "method"])

# Search with file filter
semantic_search("configuration", file_filter="src/config/**")

# Search documentation only
semantic_search("installation guide", search_scope="docs")
```

---

### rag_status

Get RAG index status and statistics.

```python
rag_status()
```

#### Returns

```python
{
    "success": True,
    "status": "ready",
    "embedding_model": "sentence-transformers/all-mpnet-base-v2",
    "embedding_provider": "local",
    "embedding_dimension": 768,
    "total_vectors": 7218,
    "index_size_mb": 21.2,
    "python_sources": {
        "files_indexed": 80,
        "total_vectors": 6502
    },
    "markdown_sources": {
        "files_indexed": 20,
        "total_vectors": 716
    },
    "entity_counts": {
        "class": 194,
        "method": 1108,
        "function": 81,
        "section": 200,
        "code_block": 509
    }
}
```

---

### rag_reindex

Trigger RAG index rebuild.

```python
rag_reindex(force=True)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | bool | False | Force complete rebuild |
| `instance_name` | str | "default" | RETER instance name |

#### Returns

```python
{
    "success": True,
    "python_sources": 80,
    "python_vectors": 6502,
    "markdown_files": 20,
    "markdown_vectors": 716,
    "total_vectors": 7218,
    "time_ms": 4500
}
```

---

### init_status

Get initialization and sync status. Always available, even during initialization.

```python
init_status()
```

#### Returns

```python
{
    "is_ready": True,
    "blocking_reason": null,
    "components": {
        "sql": {"ready": True},
        "reter": {"ready": True},
        "embedding": {"ready": True},
        "rag_code": {"ready": True},
        "rag_docs": {"ready": True}
    },
    "init": {
        "status": "ready",
        "phase": "complete",
        "progress": 1.0
    },
    "sync": {
        "status": "idle"
    }
}
```

---

### find_similar_clusters

Find clusters of semantically similar code using K-means clustering.

```python
find_similar_clusters(
    n_clusters=50,
    min_cluster_size=2,
    exclude_same_file=True,
    exclude_same_class=True
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `n_clusters` | int | 50 | Number of clusters |
| `min_cluster_size` | int | 2 | Minimum members per cluster |
| `exclude_same_file` | bool | True | Exclude same-file clusters |
| `exclude_same_class` | bool | True | Exclude same-class clusters |
| `entity_types` | list | None | Filter: class, method, function |
| `source_type` | str | None | Filter: python, markdown |

#### Returns

```python
{
    "success": True,
    "total_clusters": 15,
    "total_vectors_analyzed": 3216,
    "clusters": [
        {
            "cluster_id": 5,
            "member_count": 3,
            "unique_files": 2,
            "unique_classes": 2,
            "avg_distance": 0.15,
            "members": [
                {
                    "name": "find_large_classes",
                    "file": "advanced_python_tools.py",
                    "line": 59,
                    "entity_type": "method",
                    "class_name": "AdvancedPythonTools"
                }
            ]
        }
    ],
    "time_ms": 250
}
```

---

### find_duplicate_candidates

Find pairs of highly similar code (potential duplicates).

```python
find_duplicate_candidates(
    similarity_threshold=0.85,
    max_results=50,
    exclude_same_file=True
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `similarity_threshold` | float | 0.85 | Minimum similarity (0-1) |
| `max_results` | int | 50 | Maximum pairs to return |
| `exclude_same_file` | bool | True | Exclude same-file pairs |
| `exclude_same_class` | bool | True | Exclude same-class pairs |
| `entity_types` | list | None | Filter: method, function |

#### Returns

```python
{
    "success": True,
    "total_pairs": 12,
    "pairs": [
        {
            "similarity": 0.95,
            "entity1": {
                "name": "find_large_classes",
                "file": "advanced_python_tools.py",
                "line": 59,
                "entity_type": "method"
            },
            "entity2": {
                "name": "find_large_classes",
                "file": "code_quality.py",
                "line": 15,
                "entity_type": "method"
            }
        }
    ],
    "time_ms": 150
}
```

---

### analyze_documentation_relevance

Analyze how relevant documentation is to actual code.

```python
analyze_documentation_relevance(
    min_relevance=0.5,
    max_results=100
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `min_relevance` | float | 0.5 | Minimum similarity to consider relevant |
| `max_results` | int | 100 | Maximum docs to analyze |
| `doc_types` | list | None | Filter: section, code_block, document |
| `code_types` | list | None | Filter: class, method, function |

#### Returns

```python
{
    "success": True,
    "relevant_docs": [...],
    "orphaned_docs": [...],
    "stats": {
        "total_docs_analyzed": 100,
        "relevant_count": 75,
        "orphaned_count": 25,
        "relevance_rate": 0.75,
        "avg_similarity": 0.68
    }
}
```

## Requirements

- `semantic_search` (code): Requires RAG code index
- `semantic_search` (docs): Requires RAG docs index
- `find_similar_clusters`: Requires RAG code index
- `find_duplicate_candidates`: Requires RAG code index
- `analyze_documentation_relevance`: Requires both indexes
- `rag_reindex`: Requires RETER component
- `init_status`, `rag_status`: Always available

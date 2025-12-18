# Codeine Documentation

Codeine is an AI-powered MCP (Model Context Protocol) server for code reasoning.

## Documentation Index

### Architecture
- [Architecture Overview](./architecture.md) - System design, components, and patterns

### Tools
- [Tools Overview](./tools-overview.md) - Summary of all 19+ MCP tools

#### Session Management
- [thinking](./tools/thinking.md) - Record reasoning steps with operations
- [session](./tools/session.md) - Session lifecycle management
- [items](./tools/items.md) - Query and manage items
- [project](./tools/project.md) - Project analytics

#### Code Analysis
- [code_inspection](./tools/code-inspection.md) - Python/JS/C#/C++ analysis (26 actions)
- [recommender](./tools/recommender.md) - Refactoring recommendations (58 detectors)

#### RAG/Search
- [RAG Tools](./tools/rag-tools.md) - Semantic search and analysis
  - `semantic_search` - Vector similarity search
  - `rag_status` - Index status
  - `find_similar_clusters` - Code clustering
  - `find_duplicate_candidates` - Duplicate detection
  - `analyze_documentation_relevance` - Doc-code analysis

#### Knowledge Management
- [Knowledge Tools](./tools/knowledge-tools.md)
  - `add_knowledge` - Add knowledge to RETER
  - `add_external_directory` - Load external code
  - `quick_query` - Execute REQL queries
  - `natural_language_query` - NL to REQL

#### Visualization
- [diagram](./tools/diagram.md) - UML and project diagrams

#### Instance Management
- [instance_manager](./tools/instance-manager.md) - Manage RETER instances

## Quick Start

```python
# 1. Restore session context (CRITICAL - do this first!)
session(action="context")

# 2. Check server readiness
init_status()

# 3. Analyze your code
code_inspection(action="list_classes")

# 4. Search semantically
semantic_search("authentication handling")

# 5. Get refactoring recommendations
recommender(recommender_type="refactoring", detector_name="find_large_classes")

# 6. Record your reasoning
thinking(
    thought="Analyzing the authentication module",
    thought_number=1,
    total_thoughts=3
)

# 7. Generate diagrams
diagram(diagram_type="class_hierarchy", target="BaseTool")
```

## Configuration

Create `codeine.json` in your project root:

```json
{
  "project_root": "/path/to/project",
  "include_patterns": ["src/**/*.py"],
  "exclude_patterns": ["**/test_*.py", "**/__pycache__/**"],
  "rag_enabled": true,
  "rag_embedding_model": "sentence-transformers/all-mpnet-base-v2"
}
```

Or use environment variables:
- `RETER_PROJECT_ROOT` - Project directory
- `ANTHROPIC_API_KEY` - For LLM features
- `TRANSFORMERS_CACHE` - Embedding model cache

## Component Dependencies

| Tool Category | SQLite | RETER | RAG Code | RAG Docs |
|--------------|--------|-------|----------|----------|
| Session (thinking, session, items, project) | Required | - | - | - |
| Code Analysis (code_inspection, recommender) | - | Required | - | - |
| Semantic Search (semantic_search) | - | - | Required | Required |
| Duplication (find_similar_clusters) | - | - | Required | - |
| Documentation (analyze_documentation_relevance) | - | - | Required | Required |
| Knowledge (add_knowledge, quick_query) | - | Required | - | - |
| Diagrams - Session | Required | - | - | - |
| Diagrams - UML | - | Required | - | - |

Use `init_status()` to check component readiness.

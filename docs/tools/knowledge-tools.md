# Knowledge Management Tools

Tools for adding knowledge to and querying RETER instances.

## Overview

These tools manage the RETER knowledge graph:
- `add_knowledge` - Add knowledge from various sources
- `add_external_directory` - Load external code directories
- `quick_query` - Execute REQL queries
- `natural_language_query` - Query using natural language

---

## add_knowledge

Incrementally add knowledge to RETER's semantic memory.

### Usage

```python
add_knowledge(
    instance_name="default",
    source="path/to/file.py",
    type="python"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instance_name` | str | required | RETER instance name |
| `source` | str | required | Source content, file path, or ontology |
| `type` | str | "ontology" | Source type (see below) |
| `source_id` | str | None | Optional identifier for forgetting |

### Source Types

| Type | Description | File Extensions |
|------|-------------|-----------------|
| `ontology` | DL/SWRL ontology | .owl, .ttl |
| `python` | Python code | .py |
| `javascript` | JavaScript/TypeScript | .js, .ts, .jsx, .tsx |
| `html` | HTML documents | .html, .htm |
| `csharp` | C# code | .cs |
| `cpp` | C++ code | .cpp, .hpp, .h |

### Returns

```python
{
    "success": True,
    "items_added": 450,
    "execution_time_ms": 125,
    "source_id": "abc123|path/to/file.py"
}
```

### Examples

```python
# Add Python file
add_knowledge(
    instance_name="default",
    source="src/auth/service.py",
    type="python"
)

# Add ontology content
add_knowledge(
    instance_name="custom",
    source="""
    Class: Person
    SubClassOf: Agent
    """,
    type="ontology"
)

# Add with custom source ID
add_knowledge(
    instance_name="default",
    source="external/lib.py",
    type="python",
    source_id="external-lib-v1"
)
```

---

## add_external_directory

Load external code files from a directory into a named RETER instance.

### Usage

```python
add_external_directory(
    instance_name="external-lib",
    directory="/path/to/library",
    recursive=True,
    exclude_patterns=["test_*.py", "**/node_modules/**"]
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instance_name` | str | required | Instance name (NOT "default") |
| `directory` | str | required | Path to directory |
| `recursive` | bool | True | Search subdirectories |
| `exclude_patterns` | list | None | Glob patterns to exclude |

### Returns

```python
{
    "success": True,
    "files_loaded": {
        "python": 45,
        "javascript": 12,
        "html": 3
    },
    "total_files": {
        "python": 50,
        "javascript": 12,
        "html": 3
    },
    "total_wmes": 15000,
    "errors": [],
    "files_with_errors": [],
    "execution_time_ms": 5000
}
```

### Notes

- Cannot use "default" instance (it auto-syncs with RETER_PROJECT_ROOT)
- Use for external libraries, dependencies, or separate codebases
- Instance persists between sessions

---

## quick_query

Execute a REQL query directly against the knowledge graph.

### Usage

```python
quick_query(
    instance_name="default",
    query="SELECT ?class ?name WHERE { ?class type py:Class . ?class name ?name }",
    type="reql"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `instance_name` | str | required | RETER instance name |
| `query` | str | required | Query string |
| `type` | str | "reql" | Query type: reql, dl, pattern |

### Query Types

| Type | Description |
|------|-------------|
| `reql` | SPARQL-like query language |
| `dl` | Description Logic query |
| `pattern` | Pattern matching |

### REQL Examples

```python
# Find all classes
quick_query(
    instance_name="default",
    query="SELECT ?class WHERE { ?class type py:Class }"
)

# Find methods in a class
quick_query(
    instance_name="default",
    query="""
    SELECT ?method ?name
    WHERE {
        ?method type py:Method .
        ?method name ?name .
        ?method definedIn ?class .
        ?class name 'CodeineServer'
    }
    """
)

# Find inheritance relationships
quick_query(
    instance_name="default",
    query="""
    SELECT ?child ?parent
    WHERE {
        ?child inheritsFrom ?parent
    }
    """
)
```

### Returns

```python
{
    "success": True,
    "results": [
        {"class": "wme:123", "name": "CodeineServer"},
        {"class": "wme:124", "name": "InstanceManager"}
    ],
    "count": 45,
    "source_validity": {...},
    "warnings": []
}
```

---

## natural_language_query

Query using natural language (translated to REQL via LLM).

### Usage

```python
natural_language_query(
    question="What classes inherit from BaseTool?",
    instance_name="default"
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `question` | str | required | Natural language question |
| `instance_name` | str | "default" | RETER instance |
| `max_retries` | int | 5 | Retry attempts on errors |
| `timeout` | int | 30 | Timeout in seconds |
| `max_results` | int | 500 | Maximum results |

### Returns

```python
{
    "success": True,
    "results": [...],
    "count": 15,
    "reql_query": "SELECT ?child WHERE { ?child inheritsFrom ?parent . ?parent name 'BaseTool' }",
    "attempts": 1,
    "error": None
}
```

### Example Questions

```python
# Inheritance
natural_language_query("What classes inherit from BaseTool?")

# Method calls
natural_language_query("Find all methods that call the save function")

# Module analysis
natural_language_query("List modules with more than 5 classes")

# Parameters
natural_language_query("Which functions have the most parameters?")

# Literals
natural_language_query("Find functions with magic number 100")
natural_language_query("Show string literals containing 'error'")
```

### Notes

- Requires `ANTHROPIC_API_KEY` for LLM sampling
- Use for structural queries, not semantic search
- For semantic search, use `semantic_search` instead
- Returns the generated REQL query for learning

---

## Requirements

- All tools require RETER component to be ready
- `natural_language_query` requires Anthropic API key

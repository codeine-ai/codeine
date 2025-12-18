# instance_manager Tool

Unified tool for managing RETER instances and sources.

## Overview

The `instance_manager` tool provides operations for managing RETER instances, including listing instances, managing sources, and checking consistency.

## Basic Usage

```python
# List all instances
instance_manager(action="list")

# List sources in default instance
instance_manager(action="list_sources")

# Forget a source
instance_manager(action="forget", source="path/to/file.py")
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | str | required | Action to perform |
| `instance_name` | str | "default" | RETER instance name |
| `source` | str | None | Source ID or file path |

## Actions

### list

List all RETER instances (loaded and available snapshots).

```python
instance_manager(action="list")
```

Returns:
```python
{
    "success": True,
    "action": "list",
    "instances": {
        "default": "loaded",
        "feature-branch": "available",
        "external-lib": "loaded"
    },
    "total_count": 3,
    "loaded_count": 2,
    "available_count": 1
}
```

### list_sources

List all sources loaded in an instance.

```python
instance_manager(action="list_sources", instance_name="default")
```

Returns:
```python
{
    "success": True,
    "action": "list_sources",
    "sources": [
        "abc123|src/codeine/server.py",
        "def456|src/codeine/models.py",
        ...
    ],
    "count": 96
}
```

### get_facts

Get fact IDs for a specific source.

```python
instance_manager(
    action="get_facts",
    instance_name="default",
    source="src/codeine/server.py"
)
```

Returns:
```python
{
    "success": True,
    "action": "get_facts",
    "source": "src/codeine/server.py",
    "fact_ids": [123, 124, 125, ...],
    "count": 450
}
```

### forget

Remove all facts from a source (selective forgetting).

```python
instance_manager(
    action="forget",
    instance_name="default",
    source="src/codeine/old_module.py"
)
```

Returns:
```python
{
    "success": True,
    "action": "forget",
    "source": "src/codeine/old_module.py",
    "facts_removed": 120
}
```

### reload

Reload all modified file-based sources.

```python
instance_manager(action="reload", instance_name="default")
```

Returns:
```python
{
    "success": True,
    "action": "reload",
    "files_checked": 96,
    "files_reloaded": 3,
    "files_added": 1,
    "files_removed": 0
}
```

### check

Quick consistency check of knowledge base.

```python
instance_manager(action="check", instance_name="default")
```

Returns:
```python
{
    "success": True,
    "action": "check",
    "total_facts": 15000,
    "total_sources": 96,
    "orphaned_facts": 0,
    "missing_sources": 0,
    "status": "consistent"
}
```

## Multiple Instances

### Default Instance

The "default" instance automatically syncs with `RETER_PROJECT_ROOT`:
- Files are loaded/reloaded/forgotten based on MD5 changes
- Best for analyzing your main project

### Named Instances

Create named instances for different purposes:

```python
# Load external library
add_external_directory(
    instance_name="numpy-lib",
    directory="/path/to/numpy",
    exclude_patterns=["test_*.py"]
)

# List sources in external instance
instance_manager(action="list_sources", instance_name="numpy-lib")
```

### Instance Lifecycle

1. **Auto-created**: Instances are created on first use
2. **Persisted**: State is saved to snapshots directory
3. **Lazy-loaded**: Available snapshots load on first access
4. **Synced**: Default instance syncs with file system

## Related Tools

### add_knowledge

Add knowledge to an instance.

```python
add_knowledge(
    instance_name="default",
    source="path/to/file.py",
    type="python"
)
```

### add_external_directory

Load external code directory into a named instance.

```python
add_external_directory(
    instance_name="external",
    directory="/path/to/external/code",
    recursive=True,
    exclude_patterns=["**/test_*.py", "**/node_modules/**"]
)
```

Supported file types:
- Python: `.py`
- JavaScript: `.js`, `.mjs`, `.jsx`, `.ts`, `.tsx`
- HTML: `.html`, `.htm`
- C#: `.cs`
- C++: `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`

## Requirements

- Requires RETER component to be ready

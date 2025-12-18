# items Tool

Query and manage items (requirements, tasks, recommendations, etc.).

## Overview

The `items` tool provides CRUD operations for all item types in a session: thoughts, requirements, recommendations, tasks, milestones, decisions, constraints, and assumptions.

## Basic Usage

```python
# List all items
items(action="list")

# Get a specific item
items(action="get", item_id="REQ-001", include_relations=True)

# Update an item
items(action="update", item_id="TASK-001", updates={"status": "completed"})
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | str | "list" | Action: list, get, delete, update, clear |
| `instance_name` | str | "default" | Session instance name |
| `item_id` | str | None | Item ID (required for get/delete/update) |
| `updates` | dict | None | Fields to update (for update action) |
| `item_type` | str | None | Filter by type |
| `status` | str | None | Filter by status |
| `priority` | str | None | Filter by priority |
| `phase` | str | None | Filter by project phase |
| `category` | str | None | Filter by category |
| `source_tool` | str | None | Filter by source tool |
| `traces_to` | str | None | Items that trace to this ID |
| `traced_by` | str | None | Items traced by this ID |
| `depends_on` | str | None | Items depending on this ID |
| `blocks` | str | None | Items blocked by this ID |
| `affects` | str | None | Items affecting this file/entity |
| `start_after` | str | None | Tasks starting after this date |
| `end_before` | str | None | Tasks ending before this date |
| `include_relations` | bool | False | Include related items |
| `limit` | int | 100 | Maximum items to return |
| `offset` | int | 0 | Pagination offset |

## Actions

### `list`

Query items with filters.

```python
# List all requirements
items(action="list", item_type="requirement")

# List high-priority tasks
items(action="list", item_type="task", priority="high")

# List items from a specific recommender
items(action="list", source_tool="refactoring_improving:find_large_classes")

# List completed items
items(action="list", status="completed")
```

Returns:
```python
{
    "success": True,
    "items": [...],
    "count": 15,
    "total": 45,
    "has_more": True
}
```

### `get`

Get a single item by ID.

```python
items(action="get", item_id="REQ-001", include_relations=True)
```

Returns:
```python
{
    "success": True,
    "item": {
        "item_id": "REQ-001",
        "item_type": "requirement",
        "content": "System shall authenticate users",
        "status": "pending",
        "priority": "high",
        "created_at": "2024-01-15T10:00:00Z"
    },
    "relations": {
        "outgoing": [
            {"relation_type": "traces", "target_id": "TASK-001"}
        ],
        "incoming": [
            {"relation_type": "satisfies", "source_id": "C90F-THOUGHT-005"}
        ]
    }
}
```

### `update`

Update item fields.

```python
items(
    action="update",
    item_id="TASK-001",
    updates={
        "status": "in_progress",
        "assignee": "developer1"
    }
)
```

Returns:
```python
{
    "success": True,
    "item": {...}  # Updated item
}
```

### `delete`

Delete an item and its relations.

```python
items(action="delete", item_id="TASK-001")
```

Returns:
```python
{
    "success": True,
    "deleted": "TASK-001"
}
```

### `clear`

Delete multiple items matching filters. Requires at least one filter to prevent accidental deletion.

```python
# Clear all recommendations from a specific tool
items(
    action="clear",
    item_type="recommendation",
    source_tool="refactoring_improving:find_large_classes"
)
```

Returns:
```python
{
    "success": True,
    "items_deleted": 15,
    "relations_deleted": 23,
    "filters_used": {
        "item_type": "recommendation",
        "source_tool": "refactoring_improving:find_large_classes"
    }
}
```

## Item Types

| Type | Description |
|------|-------------|
| `thought` | Reasoning steps |
| `requirement` | System requirements |
| `recommendation` | Suggestions/recommendations |
| `task` | Work items with scheduling |
| `milestone` | Project milestones |
| `decision` | Recorded decisions |
| `constraint` | Constraints on the system |
| `assumption` | Assumptions made |

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Not started |
| `in_progress` | Work in progress |
| `completed` | Finished |
| `verified` | Verified/validated |
| `rejected` | Rejected/cancelled |
| `blocked` | Blocked by dependency |

## Priority Values

| Priority | Description |
|----------|-------------|
| `critical` | Must be done immediately |
| `high` | Important |
| `medium` | Normal priority |
| `low` | Can be deferred |

## Relation Types

| Relation | Description |
|----------|-------------|
| `traces` | Item traces to target |
| `satisfies` | Item satisfies target requirement |
| `implements` | Item implements target |
| `depends_on` | Item depends on target |
| `blocks` | Item blocks target |
| `affects` | Item affects target file/entity |
| `derives` | Item derives from target |

## Requirements

- Requires SQLite component to be ready

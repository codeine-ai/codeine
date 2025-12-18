# project Tool

Project management and analytics for tracking tasks, milestones, and progress.

## Overview

The `project` tool provides analytics and management capabilities for project planning tracked through the session system.

## Basic Usage

```python
# Get project health overview
project(action="health")

# Get critical path tasks
project(action="critical_path")

# Check overdue tasks
project(action="overdue")
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | str | required | Action to perform |
| `instance_name` | str | "default" | Session instance name |
| `task_id` | str | None | Task ID (for impact action) |
| `delay_days` | int | None | Delay days (for impact action) |
| `start_date` | str | None | Start date filter |
| `end_date` | str | None | End date filter |

## Actions

### health

Get overall project status and metrics.

```python
project(action="health")
```

Returns:
```python
{
    "success": True,
    "tasks": {
        "total": 15,
        "completed": 5,
        "in_progress": 3,
        "pending": 6,
        "blocked": 1,
        "percent_complete": 33.3
    },
    "timeline": {
        "project_start": "2024-01-15",
        "project_end": "2024-03-15",
        "days_remaining": 45,
        "days_elapsed": 15
    },
    "milestones": [
        {
            "item_id": "MS-001",
            "name": "MVP Release",
            "target_date": "2024-02-01",
            "status": "on_track"
        }
    ],
    "recommendations": {
        "total": 25,
        "completed": 8,
        "pending": 17,
        "progress_percent": 32
    }
}
```

### critical_path

Get tasks on the critical path (zero float).

```python
project(action="critical_path")
```

Returns:
```python
{
    "success": True,
    "critical_tasks": [
        {
            "item_id": "TASK-001",
            "name": "Implement auth",
            "start_date": "2024-01-15",
            "end_date": "2024-01-20",
            "duration_days": 5,
            "dependencies": ["TASK-002"],
            "float": 0
        }
    ],
    "total_duration": 45,
    "path_length": 8
}
```

### overdue

Get tasks past their end date.

```python
project(action="overdue")
```

Returns:
```python
{
    "success": True,
    "overdue_tasks": [
        {
            "item_id": "TASK-003",
            "name": "Write tests",
            "end_date": "2024-01-18",
            "days_overdue": 3,
            "status": "in_progress",
            "blocked_by": []
        }
    ],
    "total_overdue": 2
}
```

### impact

Analyze impact of delaying a specific task.

```python
project(
    action="impact",
    task_id="TASK-001",
    delay_days=5
)
```

Returns:
```python
{
    "success": True,
    "delayed_task": {
        "item_id": "TASK-001",
        "name": "Implement auth",
        "original_end": "2024-01-20",
        "new_end": "2024-01-25"
    },
    "affected_tasks": [
        {
            "item_id": "TASK-002",
            "name": "Write auth tests",
            "original_start": "2024-01-21",
            "new_start": "2024-01-26",
            "delay_days": 5
        }
    ],
    "affected_milestones": [
        {
            "item_id": "MS-001",
            "name": "MVP Release",
            "at_risk": True,
            "original_date": "2024-02-01",
            "projected_date": "2024-02-06"
        }
    ],
    "total_project_delay": 5
}
```

## Task Scheduling

Tasks can be scheduled using the `thinking` tool:

```python
thinking(
    thought="Planning implementation phase",
    thought_number=1,
    total_thoughts=3,
    operations={
        "task": {
            "name": "Implement authentication",
            "start_date": "2024-01-15",
            "duration_days": 5,
            "priority": "high",
            "depends_on": ["TASK-000"]
        }
    }
)
```

## Milestones

Create milestones to track major deliverables:

```python
thinking(
    thought="Setting MVP milestone",
    thought_number=2,
    total_thoughts=3,
    operations={
        "milestone": {
            "name": "MVP Release",
            "target_date": "2024-02-01",
            "criteria": ["Auth complete", "Tests passing"]
        }
    }
)
```

## Workflow

1. **Start session** with project dates:
   ```python
   session(
       action="start",
       goal="Build feature X",
       project_start="2024-01-15",
       project_end="2024-03-15"
   )
   ```

2. **Create tasks** via thinking tool

3. **Monitor progress**:
   ```python
   project(action="health")
   ```

4. **Check critical path**:
   ```python
   project(action="critical_path")
   ```

5. **Analyze delays**:
   ```python
   project(action="impact", task_id="TASK-001", delay_days=3)
   ```

6. **Visualize**:
   ```python
   diagram(diagram_type="gantt")
   ```

## Requirements

- Requires SQLite component to be ready

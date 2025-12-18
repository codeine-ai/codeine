# recommender Tool

Unified recommender tool for code analysis and improvement recommendations.

## Overview

The `recommender` tool provides 58+ detectors across three categories:
- **Refactoring**: Code smells and refactoring opportunities
- **Test Coverage**: Test coverage gaps and suggestions
- **Documentation Maintenance**: Documentation issues

## Basic Usage

```python
# List all refactoring detectors
recommender(recommender_type="refactoring")

# Run a specific detector
recommender(
    recommender_type="refactoring",
    detector_name="find_large_classes"
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `recommender_type` | str | required | Type: refactoring, test_coverage, documentation_maintenance |
| `detector_name` | str | None | Specific detector to run (None = list all) |
| `instance_name` | str | "default" | RETER instance to analyze |
| `session_instance` | str | "default" | Session for storing recommendations |
| `categories` | list | None | Filter by category |
| `severities` | list | None | Filter by severity: low, medium, high, critical |
| `detector_type` | str | "all" | For refactoring: all, improving, patterns |
| `params` | dict | None | Override detector defaults |
| `create_tasks` | bool | False | Auto-create tasks from findings |
| `link_to_thought` | str | None | Link recommendations to thought ID |

## Refactoring Recommender

### List Mode

```python
recommender(recommender_type="refactoring")
```

Returns available detectors organized by category.

### Detector Categories

#### Code Smells

| Detector | Description | Severity |
|----------|-------------|----------|
| `find_large_classes` | Classes with too many methods (God classes) | high |
| `find_long_parameter_lists` | Functions with too many parameters | medium |
| `find_magic_numbers` | Numeric literals that should be constants | medium |
| `detect_long_functions` | Functions exceeding line count threshold | medium |
| `detect_data_classes` | Classes with only getters/setters | low |
| `detect_feature_envy` | Methods calling other classes more than own | high |
| `detect_refused_bequest` | Subclasses not using inherited methods | medium |
| `find_message_chains` | Long method call chains | medium |
| `find_global_data` | Module-level mutable assignments | high |
| `find_speculative_generality` | Abstract classes with only 1 subclass | low |
| `find_flag_arguments` | Boolean parameters controlling behavior | medium |

#### Refactoring Opportunities

| Detector | Description | Severity |
|----------|-------------|----------|
| `find_data_clumps` | Parameter groups appearing together | medium |
| `find_attribute_data_clumps` | Attribute groups in multiple classes | medium |
| `find_function_groups` | Functions operating on shared data | medium |
| `find_extract_function_opportunities` | Candidates for Extract Function | medium |
| `find_inline_function_candidates` | Trivial functions called once | low |
| `find_duplicate_parameter_lists` | Identical parameter signatures | medium |
| `find_shotgun_surgery` | High fan-in from many modules | high |
| `find_middle_man` | Classes that just delegate | low |
| `find_extract_class_opportunities` | Classes that should be split | high |
| `find_inline_class_opportunities` | Trivial classes to inline | low |
| `find_primitive_obsession` | Primitives that should be value objects | medium |

#### Inheritance

| Detector | Description | Severity |
|----------|-------------|----------|
| `find_pull_up_method_candidates` | Duplicate methods in siblings | medium |
| `find_push_down_method_candidates` | Superclass methods used by some subclasses | medium |
| `find_remove_subclass_candidates` | Trivial subclasses | low |
| `find_extract_superclass_candidates` | Similar methods needing shared superclass | medium |
| `find_collapse_hierarchy_candidates` | Nearly identical parent-child pairs | low |

#### Exception Handling

| Detector | Description | Severity |
|----------|-------------|----------|
| `detect_silent_exception_swallowing` | Empty except blocks | critical |
| `detect_too_general_exceptions` | Catching overly broad exceptions | high |
| `detect_general_exception_raising` | Raising generic Exception | medium |
| `detect_error_codes_over_exceptions` | Returning error codes instead of raising | medium |
| `detect_finally_without_context_manager` | try/finally that should use 'with' | medium |

#### Duplication (RAG-based)

| Detector | Description | Severity |
|----------|-------------|----------|
| `detect_duplicate_code` | Semantically similar code | high |
| `find_similar_clusters` | Clusters of similar code | medium |
| `detect_extraction_opportunities` | Similar blocks for extraction | high |

### Running a Detector

```python
recommender(
    recommender_type="refactoring",
    detector_name="find_large_classes",
    params={"threshold": 15}
)
```

Returns:
```python
{
    "success": True,
    "detector": "find_large_classes",
    "findings": [
        {
            "name": "CodeineServer",
            "file": "src/codeine/server.py",
            "line": 120,
            "method_count": 25,
            "severity": "high",
            "suggestion": "Consider extracting service classes"
        }
    ],
    "count": 3,
    "recommendations_created": 3
}
```

## Test Coverage Recommender

```python
# List detectors
recommender(recommender_type="test_coverage")

# Run detector
recommender(
    recommender_type="test_coverage",
    detector_name="untested_classes"
)
```

### Detectors

| Detector | Description |
|----------|-------------|
| `untested_classes` | Classes without test coverage |
| `untested_functions` | Functions without tests |
| `untested_methods` | Methods without tests |
| `low_coverage_modules` | Modules with few tests |
| `missing_edge_case_tests` | Missing boundary tests |

## Documentation Maintenance Recommender

```python
# List detectors
recommender(recommender_type="documentation_maintenance")

# Run detector
recommender(
    recommender_type="documentation_maintenance",
    detector_name="orphaned_sections"
)
```

### Detectors

| Detector | Description |
|----------|-------------|
| `orphaned_sections` | Doc sections not matching code |
| `undocumented_code` | Code without docstrings |
| `outdated_examples` | Code examples that may be stale |
| `missing_api_docs` | Public API without documentation |

## Creating Tasks

Auto-create tasks from high-priority findings:

```python
recommender(
    recommender_type="refactoring",
    detector_name="detect_silent_exception_swallowing",
    create_tasks=True
)
```

## Linking to Thoughts

Link recommendations to your reasoning:

```python
recommender(
    recommender_type="refactoring",
    detector_name="find_large_classes",
    link_to_thought="C90F-THOUGHT-005"
)
```

## Requirements

- Requires RETER component to be ready
- RAG-based detectors require RAG index

# code_inspection Tool

Unified code inspection tool for analyzing Python, JavaScript, HTML, C#, and C++ code.

## Overview

The `code_inspection` tool consolidates 26 analysis operations into a single unified interface. It queries the RETER knowledge graph to analyze code structure, find patterns, and understand dependencies.

## Basic Usage

```python
code_inspection(
    action="list_classes",
    instance_name="default",
    limit=100
)
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action` | str | required | Operation to perform (see Actions below) |
| `instance_name` | str | "default" | RETER instance name |
| `target` | str | None | Target entity name (class, method, function) |
| `module` | str | None | Module name filter |
| `limit` | int | 100 | Maximum results to return |
| `offset` | int | 0 | Pagination offset |
| `format` | str | "json" | Output format: json, markdown, mermaid |
| `include_methods` | bool | True | Include methods in class descriptions |
| `include_attributes` | bool | True | Include attributes in class descriptions |
| `include_docstrings` | bool | True | Include docstrings |
| `summary_only` | bool | False | Return summary only |
| `params` | dict | None | Additional action-specific parameters |
| `language` | str | "oo" | Language filter: oo, python, javascript, html |

## Language Support

| Value | Description |
|-------|-------------|
| `oo` | Language-independent (matches all languages) |
| `python` or `py` | Python only |
| `javascript` or `js` | JavaScript only |
| `html` or `htm` | HTML documents only |

## Actions

### Structure/Navigation

#### `list_modules`
List all modules in the codebase.

```python
code_inspection(action="list_modules")
```

Returns: `modules[]`, `count`, `total_count`

#### `list_classes`
List all classes, optionally filtered by module.

```python
code_inspection(action="list_classes", module="codeine.services")
```

Returns: `classes[]`, `count`, `has_more`

#### `list_functions`
List top-level functions, optionally filtered by module.

```python
code_inspection(action="list_functions", module="codeine.utils")
```

Returns: `functions[]`, `count`, `has_more`

#### `describe_class`
Get detailed class description with methods and attributes.

```python
code_inspection(
    action="describe_class",
    target="CodeineServer",
    include_methods=True,
    include_attributes=True
)
```

Returns: `class_info`, `methods[]`, `attributes[]`

#### `get_docstring`
Get the docstring of a class, method, or function.

```python
code_inspection(action="get_docstring", target="CodeineServer")
```

Returns: `docstring`, `entity_type`

#### `get_method_signature`
Get method signature with parameters and return type.

```python
code_inspection(action="get_method_signature", target="run")
```

Returns: `signature`, `parameters[]`, `return_type`

#### `get_class_hierarchy`
Get inheritance hierarchy (parents and children).

```python
code_inspection(action="get_class_hierarchy", target="BaseTool")
```

Returns: `parents[]`, `children[]`, `hierarchy_depth`

#### `get_package_structure`
Get package/module directory structure.

```python
code_inspection(action="get_package_structure")
```

Returns: `modules[]`, `by_directory{}`, `module_count`

### Search/Find

#### `find_usages`
Find where a class/method/function is called in the codebase.

```python
code_inspection(action="find_usages", target="truncate_response")
```

Returns: `usages[]`, `count`

#### `find_subclasses`
Find all subclasses of a class (direct and indirect).

```python
code_inspection(action="find_subclasses", target="BaseTool")
```

Returns: `subclasses[]`, `count`

#### `find_callers`
Find all functions/methods that call the target (recursive).

```python
code_inspection(action="find_callers", target="save_state")
```

Returns: `callers[]`, `count`, `call_depth`

#### `find_callees`
Find all functions/methods called by the target (recursive).

```python
code_inspection(action="find_callees", target="initialize")
```

Returns: `callees[]`, `count`, `call_depth`

#### `find_decorators`
Find all decorator usages, optionally by name.

```python
code_inspection(action="find_decorators", target="app.tool")
```

Returns: `decorators[]`, `count`

#### `find_tests`
Find test classes/functions for a module, class, or function.

```python
code_inspection(action="find_tests", target="CodeineServer")
```

Returns: `tests_found[]`, `suggestions[]`

### Analysis

#### `analyze_dependencies`
Analyze module dependency graph.

```python
code_inspection(action="analyze_dependencies")
```

Returns: `dependencies[]`, `circular_dependencies[]`, `summary`

#### `get_imports`
Get complete module import dependency graph.

```python
code_inspection(action="get_imports")
```

Returns: `imports[]`, `import_graph{}`, `external_deps[]`

#### `get_external_deps`
Get external (pip) package dependencies.

```python
code_inspection(action="get_external_deps")
```

Returns: `external_packages[]`, `by_module{}`

#### `predict_impact`
Predict impact of changing a function/method/class.

```python
code_inspection(action="predict_impact", target="ReterWrapper")
```

Returns: `affected_files[]`, `affected_entities[]`, `risk_level`

#### `get_complexity`
Calculate complexity metrics for the codebase.

```python
code_inspection(action="get_complexity")
```

Returns: `class_complexity{}`, `parameter_complexity{}`, `inheritance_complexity{}`, `call_complexity{}`

#### `get_magic_methods`
Find all magic methods (__init__, __str__, etc.).

```python
code_inspection(action="get_magic_methods")
```

Returns: `magic_methods[]`, `by_class{}`, `count`

#### `get_interfaces`
Find classes implementing abstract base classes/interfaces.

```python
code_inspection(action="get_interfaces", target="ABC")
```

Returns: `implementations[]`, `count`

#### `get_public_api`
Get all public (non-underscore) classes and functions.

```python
code_inspection(action="get_public_api")
```

Returns: `entities[]`, `count`, `by_type{}`

#### `get_type_hints`
Extract all type annotations from parameters and returns.

```python
code_inspection(action="get_type_hints")
```

Returns: `type_hints[]`, `coverage_stats{}`

#### `get_api_docs`
Extract all API documentation from docstrings.

```python
code_inspection(action="get_api_docs")
```

Returns: `documentation{}`, `coverage_stats{}`

#### `get_exceptions`
Get exception class hierarchy.

```python
code_inspection(action="get_exceptions")
```

Returns: `exceptions[]`, `hierarchy{}`, `custom_exceptions[]`

#### `get_architecture`
Generate high-level architectural overview.

```python
code_inspection(action="get_architecture", format="markdown")
```

Returns: `overview`, `layers[]`, `components[]`

## Requirements

- Requires RETER component to be ready
- Use `init_status()` to check readiness

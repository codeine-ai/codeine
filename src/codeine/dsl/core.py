"""
CADSL Core - Monadic Pipeline and Tool Type Classes

This module provides the core abstractions for the Code Analysis DSL,
built on category theory foundations from catpy:

- Pipeline: A Monad for composable data transformation chains
- Step: A function wrapper that transforms data within the pipeline
- Query/Detector/Diagram: Tool type wrappers

The Pipeline follows monad laws:
  1) Left identity:  Pipeline.pure(x).bind(f) == f(x)
  2) Right identity: m.bind(Pipeline.pure) == m
  3) Associativity:  m.bind(f).bind(g) == m.bind(lambda x: f(x).bind(g))
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    TypeVar, Generic, Callable, List, Dict, Any, Optional,
    Union, Tuple, Iterator, Sequence
)
from enum import Enum
from abc import ABC, abstractmethod

# Import category theory foundations
from .catpy import (
    Functor, Applicative, Monad,
    Result, Ok, Err,
    Maybe, Just, Nothing,
    ListF,
    PipelineError, PipelineResult,
    pipeline_ok, pipeline_err,
    compose, identity
)

T = TypeVar("T")
U = TypeVar("U")
V = TypeVar("V")


# =============================================================================
# Re-export catpy types for convenience
# =============================================================================

__all__ = [
    # From catpy
    "Functor", "Applicative", "Monad",
    "Result", "Ok", "Err",
    "Maybe", "Just", "Nothing",
    "ListF",
    "PipelineError", "PipelineResult",
    "pipeline_ok", "pipeline_err",
    "compose", "identity",
    # Core types
    "Context", "Source", "Step", "Pipeline",
    "Query", "Detector", "Diagram",
    "ToolSpec", "ParamSpec", "ToolType",
    # Source builders
    "reql", "rag", "value",
]


# =============================================================================
# Pipeline Context
# =============================================================================

@dataclass
class Context:
    """Execution context for pipelines."""
    reter: Any  # RETER instance
    params: Dict[str, Any] = field(default_factory=dict)
    language: str = "oo"
    instance_name: str = "default"

    def get_param(self, name: str, default: Any = None) -> Any:
        """Get a parameter value."""
        return self.params.get(name, default)

    def get(self, name: str, default: Any = None) -> Any:
        """Get a value from params (alias for get_param)."""
        return self.params.get(name, default)

    def with_params(self, **kwargs) -> "Context":
        """Create a new context with additional params."""
        new_params = {**self.params, **kwargs}
        return Context(
            reter=self.reter,
            params=new_params,
            language=self.language,
            instance_name=self.instance_name
        )


# =============================================================================
# Sources (Query Origins) - Functors that produce initial data
# =============================================================================

class Source(ABC, Generic[T]):
    """
    Abstract base for pipeline data sources.

    A Source is a functor that produces data when executed in a context.
    """

    @abstractmethod
    def execute(self, ctx: Context) -> PipelineResult[T]:
        """Execute the source and return data wrapped in Result."""
        pass

    def fmap(self, f: Callable[[T], U]) -> "MappedSource[T, U]":
        """Map a function over the source output."""
        return MappedSource(self, f)


@dataclass
class MappedSource(Source[U], Generic[T, U]):
    """A source with a mapped transformation."""
    inner: Source[T]
    transform: Callable[[T], U]

    def execute(self, ctx: Context) -> PipelineResult[U]:
        result = self.inner.execute(ctx)
        return result.fmap(self.transform)


@dataclass
class REQLSource(Source[List[Dict[str, Any]]]):
    """REQL query source."""
    query: str

    # Language-specific concept placeholders that get resolved
    CONCEPT_PLACEHOLDERS = [
        "CodeEntity", "Module", "Class", "Function", "Method", "Constructor",
        "Parameter", "Import", "Export", "Assignment", "Field", "Attribute",
        "TryBlock", "CatchClause", "ThrowStatement", "ReturnStatement", "Call",
        "ExceptHandler", "RaiseStatement", "FinallyBlock", "ArrowFunction",
        "Variable", "FinallyClause", "Namespace", "TranslationUnit", "Struct",
        "Destructor", "Operator", "Enum", "EnumClass", "Enumerator",
        "UsingDirective", "UsingDeclaration", "Inheritance",
        "Document", "Element", "Script", "ScriptReference", "StyleSheet",
        "Form", "FormInput", "Link", "EventHandler", "Meta", "Image", "Iframe",
    ]

    def execute(self, ctx: Context) -> PipelineResult[List[Dict[str, Any]]]:
        """Execute REQL query against RETER."""
        try:
            from codeine.services.language_support import LanguageSupport

            query = self.query

            # Substitute language-specific concept placeholders: {Class} -> py:Class
            for concept in self.CONCEPT_PLACEHOLDERS:
                placeholder = "{" + concept + "}"
                if placeholder in query:
                    resolved = LanguageSupport.concept(concept, ctx.language)
                    query = query.replace(placeholder, resolved)

            # Substitute parameters in query: {target} -> actual value
            for key, value in ctx.params.items():
                placeholder = "{" + key + "}"
                if placeholder in query:
                    query = query.replace(placeholder, str(value))

            # Execute query
            table = ctx.reter.reql(query)

            # Convert PyArrow table to list of dicts
            if table is None or table.num_rows == 0:
                return pipeline_ok([])
            results = table.to_pylist()
            return pipeline_ok(results)
        except Exception as e:
            return pipeline_err("reql", f"Query failed: {e}: {query}", e)


@dataclass
class ValueSource(Source[T], Generic[T]):
    """Literal value source."""
    value: T

    def execute(self, ctx: Context) -> PipelineResult[T]:
        return pipeline_ok(self.value)


@dataclass
class RAGSource(Source[List[Dict[str, Any]]]):
    """RAG semantic search source."""
    query: str
    top_k: int = 10
    entity_types: Optional[List[str]] = None

    def execute(self, ctx: Context) -> PipelineResult[List[Dict[str, Any]]]:
        """Execute semantic search."""
        try:
            # This would integrate with the RAG system
            # For now, return empty result as placeholder
            return pipeline_ok([])
        except Exception as e:
            return pipeline_err("rag", f"Semantic search failed: {e}", e)


# =============================================================================
# Step - Kleisli Arrow for Pipeline
# =============================================================================

class Step(ABC, Generic[T, U]):
    """
    A step in a pipeline - a Kleisli arrow: T -> Result[U, PipelineError]

    Steps are the building blocks of pipelines. Each step transforms
    input data and returns a Result, allowing for error propagation.
    """

    @abstractmethod
    def execute(self, data: T, ctx: Optional["Context"] = None) -> PipelineResult[U]:
        """Transform input data and return result."""
        pass

    def _resolve_param(self, value: Any, ctx: Optional["Context"]) -> Any:
        """Resolve {param} placeholders from context."""
        if ctx is None or not isinstance(value, str):
            return value
        if value.startswith("{") and value.endswith("}"):
            param_name = value[1:-1]
            return ctx.params.get(param_name, value)
        return value

    def __rshift__(self, other: "Step[U, V]") -> "ComposedStep[T, U, V]":
        """Compose steps: step1 >> step2"""
        return ComposedStep(self, other)

    def and_then(self, other: "Step[U, V]") -> "ComposedStep[T, U, V]":
        """Compose steps: step1.and_then(step2)"""
        return self >> other


@dataclass
class ComposedStep(Step[T, V], Generic[T, U, V]):
    """Composition of two steps (Kleisli composition)."""
    first: Step[T, U]
    second: Step[U, V]

    def execute(self, data: T, ctx: Optional["Context"] = None) -> PipelineResult[V]:
        result = self.first.execute(data, ctx)
        if result.is_err():
            return result  # type: ignore
        return self.second.execute(result.unwrap(), ctx)


@dataclass
class FilterStep(Step[List[T], List[T]], Generic[T]):
    """Filter items based on predicate."""
    predicate: Callable[[T], bool]
    condition: Optional[Callable[[], bool]] = None  # when/unless condition

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[T]]:
        if self.condition is not None and not self.condition():
            return pipeline_ok(data)  # Skip filter if condition not met
        try:
            # Try to call predicate with context if it accepts 2 parameters
            import inspect
            try:
                sig = inspect.signature(self.predicate)
                if len(sig.parameters) >= 2:
                    return pipeline_ok([item for item in data if self.predicate(item, ctx)])
                else:
                    return pipeline_ok([item for item in data if self.predicate(item)])
            except (ValueError, TypeError):
                return pipeline_ok([item for item in data if self.predicate(item)])
        except Exception as e:
            return pipeline_err("filter", f"Filter failed: {e}", e)


@dataclass
class SelectStep(Step[List[Dict], List[Dict]]):
    """Select/rename fields from items."""
    fields: Dict[str, str]  # output_name -> source_name

    def execute(self, data: List[Dict], ctx: Optional["Context"] = None) -> PipelineResult[List[Dict]]:
        try:
            result = []
            for item in data:
                new_item = {}
                for out_name, src_name in self.fields.items():
                    # Normalize output name (strip ? prefix)
                    clean_out = out_name.lstrip("?")
                    # Try exact match first
                    if src_name in item:
                        new_item[clean_out] = item[src_name]
                    # Try with ? prefix (REQL variables)
                    elif not src_name.startswith("?") and f"?{src_name}" in item:
                        new_item[clean_out] = item[f"?{src_name}"]
                    # Try output name as fallback
                    elif out_name in item:
                        new_item[clean_out] = item[out_name]
                    # Try output name with ? prefix
                    elif not out_name.startswith("?") and f"?{out_name}" in item:
                        new_item[clean_out] = item[f"?{out_name}"]
                result.append(new_item)
            return pipeline_ok(result)
        except Exception as e:
            return pipeline_err("select", f"Select failed: {e}", e)


@dataclass
class OrderByStep(Step[List[Dict], List[Dict]]):
    """Sort items by field."""
    field_name: str
    descending: bool = False

    def execute(self, data: List[Dict], ctx: Optional["Context"] = None) -> PipelineResult[List[Dict]]:
        try:
            # Handle both 'name' and '?name' field variants
            def get_value(x):
                if self.field_name in x:
                    return x.get(self.field_name, "")
                elif not self.field_name.startswith("?") and f"?{self.field_name}" in x:
                    return x.get(f"?{self.field_name}", "")
                return ""
            return pipeline_ok(sorted(data, key=get_value, reverse=self.descending))
        except Exception as e:
            return pipeline_err("order_by", f"Sort failed: {e}", e)


@dataclass
class LimitStep(Step[List[T], List[T]], Generic[T]):
    """Limit number of results."""
    count: int

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[T]]:
        return pipeline_ok(data[:self.count])


@dataclass
class OffsetStep(Step[List[T], List[T]], Generic[T]):
    """Skip first N results."""
    count: int

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[T]]:
        return pipeline_ok(data[self.count:])


@dataclass
class MapStep(Step[List[T], List[U]], Generic[T, U]):
    """Transform each item using fmap semantics."""
    transform: Callable[[T], U]

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[U]]:
        try:
            return pipeline_ok([self.transform(item) for item in data])
        except Exception as e:
            return pipeline_err("map", f"Map failed: {e}", e)


@dataclass
class FlatMapStep(Step[List[T], List[U]], Generic[T, U]):
    """Transform and flatten using bind semantics."""
    transform: Callable[[T], List[U]]

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[U]]:
        try:
            result = []
            for item in data:
                result.extend(self.transform(item))
            return pipeline_ok(result)
        except Exception as e:
            return pipeline_err("flat_map", f"FlatMap failed: {e}", e)


@dataclass
class GroupByStep(Step[List[Dict], Dict[str, Any]]):
    """Group items by field value or key function."""
    field_name: Optional[str] = None
    key_fn: Optional[Callable[[Dict], str]] = None
    aggregate_fn: Optional[Callable[[List[Dict]], Any]] = None

    def execute(self, data: List[Dict], ctx: Optional["Context"] = None) -> PipelineResult[Dict[str, Any]]:
        try:
            groups: Dict[str, List[Dict]] = {}
            for item in data:
                if self.key_fn:
                    key = str(self.key_fn(item))
                elif self.field_name:
                    key = str(item.get(self.field_name, ""))
                else:
                    key = "default"
                if key not in groups:
                    groups[key] = []
                groups[key].append(item)

            # Apply aggregation if provided
            if self.aggregate_fn:
                result = {}
                for key, items in groups.items():
                    # Try to call with context if the function accepts it
                    try:
                        import inspect
                        sig = inspect.signature(self.aggregate_fn)
                        if len(sig.parameters) >= 2:
                            result[key] = self.aggregate_fn(items, ctx)
                        else:
                            result[key] = self.aggregate_fn(items)
                    except (ValueError, TypeError):
                        result[key] = self.aggregate_fn(items)
                return pipeline_ok({"items": result})

            return pipeline_ok(groups)
        except Exception as e:
            return pipeline_err("group_by", f"Group by failed: {e}", e)


@dataclass
class AggregateStep(Step[List[Dict], Dict[str, Any]]):
    """Aggregate data with specified functions."""
    aggregations: Dict[str, Tuple[str, str]]  # output -> (field, func)

    def execute(self, data: List[Dict], ctx: Optional["Context"] = None) -> PipelineResult[Dict[str, Any]]:
        try:
            result = {"count": len(data)}
            for out_name, (field_name, func) in self.aggregations.items():
                values = [item.get(field_name) for item in data if item.get(field_name) is not None]
                if func == "count":
                    result[out_name] = len(values)
                elif func == "sum":
                    result[out_name] = sum(values)
                elif func == "avg":
                    result[out_name] = sum(values) / len(values) if values else 0
                elif func == "min":
                    result[out_name] = min(values) if values else None
                elif func == "max":
                    result[out_name] = max(values) if values else None
            return pipeline_ok(result)
        except Exception as e:
            return pipeline_err("aggregate", f"Aggregation failed: {e}", e)


@dataclass
class FlattenStep(Step[List[List[T]], List[T]], Generic[T]):
    """Flatten nested lists (join in monad terms)."""

    def execute(self, data: List[List[T]], ctx: Optional["Context"] = None) -> PipelineResult[List[T]]:
        try:
            return pipeline_ok([item for sublist in data for item in sublist])
        except Exception as e:
            return pipeline_err("flatten", f"Flatten failed: {e}", e)


@dataclass
class UniqueStep(Step[List[T], List[T]], Generic[T]):
    """Remove duplicates based on key."""
    key: Optional[Callable[[T], Any]] = None

    def execute(self, data: List[T], ctx: Optional["Context"] = None) -> PipelineResult[List[T]]:
        try:
            if self.key:
                seen = set()
                result = []
                for item in data:
                    k = self.key(item)
                    if k not in seen:
                        seen.add(k)
                        result.append(item)
                return pipeline_ok(result)
            else:
                seen = set()
                result = []
                for item in data:
                    if isinstance(item, dict):
                        k = tuple(sorted(item.items()))
                    else:
                        k = item
                    if k not in seen:
                        seen.add(k)
                        result.append(item)
                return pipeline_ok(result)
        except Exception as e:
            return pipeline_err("unique", f"Unique failed: {e}", e)


@dataclass
class TapStep(Step[T, T], Generic[T]):
    """Execute a side effect function and pass through data unchanged."""
    fn: Callable[[T], Any]

    def execute(self, data: T, ctx: Optional["Context"] = None) -> PipelineResult[T]:
        try:
            # Execute side effect - result is stored but data passes through
            # Try to call with context if the function accepts it
            try:
                import inspect
                sig = inspect.signature(self.fn)
                if len(sig.parameters) >= 2:
                    result = self.fn(data, ctx)
                else:
                    result = self.fn(data)
            except (ValueError, TypeError):
                result = self.fn(data)
            # If the tap function returns something useful, attach it to the data
            if result is not None and isinstance(data, (list, dict)):
                # Store tap result for later use (e.g., by render step)
                if isinstance(data, list):
                    return pipeline_ok({"items": data, "_tap_result": result})
                elif isinstance(data, dict):
                    data_copy = dict(data)
                    data_copy["_tap_result"] = result
                    return pipeline_ok(data_copy)
            return pipeline_ok(data)
        except Exception as e:
            return pipeline_err("tap", f"Tap failed: {e}", e)


@dataclass
class RenderStep(Step[Any, str]):
    """Render data into a formatted string."""
    format: str
    renderer: Callable[[Any, str], Any]

    def execute(self, data: Any, ctx: Optional["Context"] = None) -> PipelineResult[str]:
        try:
            # If data has tap result, use that
            if isinstance(data, dict) and "_tap_result" in data:
                render_data = data["_tap_result"]
            else:
                render_data = data
            # Resolve format from context params if it's a placeholder
            fmt = self._resolve_param(self.format, ctx)
            result = self.renderer(render_data, fmt)
            return pipeline_ok(result)
        except Exception as e:
            return pipeline_err("render", f"Render failed: {e}", e)


# =============================================================================
# Pipeline Monad
# =============================================================================

@dataclass
class Pipeline(Monad[T], Generic[T]):
    """
    A monadic, composable, lazy data transformation pipeline.

    Pipeline is a Monad where:
    - pure(x) creates a pipeline that yields x
    - bind(f) chains a function that returns another pipeline
    - fmap(f) transforms the pipeline output

    The pipeline is lazy - it only executes when run() is called.

    Example:
        pipeline = (
            Pipeline.from_reql("SELECT ...")
            .filter(lambda x: x["count"] > 10)
            .fmap(lambda x: x["name"])  # Functor operation
            .order_by("-count")
            .limit(100)
        )
        result = pipeline.run(context)  # Result[T, PipelineError]
    """
    _source: Source[Any]
    _steps: List[Step] = field(default_factory=list)
    _emit_key: Optional[str] = None

    # -------------------------------------------------------------------------
    # Monad Implementation
    # -------------------------------------------------------------------------

    @classmethod
    def pure(cls, value: U) -> "Pipeline[U]":
        """Lift a value into a pipeline (Applicative.pure)."""
        return cls(_source=ValueSource(value))

    def bind(self, f: Callable[[T], "Pipeline[U]"]) -> "Pipeline[U]":
        """
        Chain a function that returns a pipeline (Monad.bind).

        This is the core monadic operation that allows sequencing
        computations where each step can produce a new pipeline.
        """
        # Create a new pipeline that, when executed:
        # 1. Runs this pipeline
        # 2. Applies f to the result to get a new pipeline
        # 3. Runs that new pipeline
        return BoundPipeline(self, f)

    def fmap(self, f: Callable[[T], U]) -> "Pipeline[U]":
        """Map a function over the pipeline output (Functor.fmap)."""
        # For lists, we want to map over each element
        # This creates a new pipeline with a map step
        new_steps = self._steps + [MapStep(f)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def ap(self, x: "Pipeline[T]") -> "Pipeline[U]":
        """Apply a wrapped function to a wrapped value (Applicative.ap)."""
        # Default monad implementation
        return self.bind(lambda f: x.bind(lambda a: Pipeline.pure(f(a))))

    # -------------------------------------------------------------------------
    # Constructors
    # -------------------------------------------------------------------------

    @classmethod
    def from_source(cls, source: Source[T]) -> "Pipeline[T]":
        """Create pipeline from a custom Source."""
        return cls(_source=source)

    @classmethod
    def from_reql(cls, query: str) -> "Pipeline[List[Dict]]":
        """Create pipeline from REQL query."""
        return cls(_source=REQLSource(query))

    @classmethod
    def from_value(cls, value: T) -> "Pipeline[T]":
        """Create pipeline from literal value."""
        return cls(_source=ValueSource(value))

    @classmethod
    def from_rag(cls, query: str, top_k: int = 10,
                 entity_types: Optional[List[str]] = None) -> "Pipeline[List[Dict]]":
        """Create pipeline from RAG semantic search."""
        return cls(_source=RAGSource(query, top_k, entity_types))

    # -------------------------------------------------------------------------
    # Transformation Methods (fluent API using Steps)
    # -------------------------------------------------------------------------

    def filter(self, predicate: Callable[[Any], bool],
               when: Optional[Callable[[], bool]] = None) -> "Pipeline":
        """Filter items matching predicate."""
        new_steps = self._steps + [FilterStep(predicate, when)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def select(self, *fields: str, **renames: str) -> "Pipeline":
        """Select and optionally rename fields."""
        field_map = {f: f for f in fields}
        field_map.update(renames)
        new_steps = self._steps + [SelectStep(field_map)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def order_by(self, field: str) -> "Pipeline":
        """Sort by field. Prefix with - for descending."""
        descending = field.startswith("-")
        if descending:
            field = field[1:]
        new_steps = self._steps + [OrderByStep(field, descending)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def limit(self, count: int) -> "Pipeline":
        """Limit number of results."""
        new_steps = self._steps + [LimitStep(count)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def offset(self, count: int) -> "Pipeline":
        """Skip first N results."""
        new_steps = self._steps + [OffsetStep(count)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def map(self, transform: Callable[[Any], Any]) -> "Pipeline":
        """Transform each item (alias for fmap on list elements)."""
        new_steps = self._steps + [MapStep(transform)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def flat_map(self, transform: Callable[[Any], List]) -> "Pipeline":
        """Transform and flatten (monadic bind for lists)."""
        new_steps = self._steps + [FlatMapStep(transform)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def group_by(self, field: Optional[str] = None, *,
                 key: Optional[Callable[[Any], str]] = None,
                 aggregate: Optional[Callable[[List], Any]] = None) -> "Pipeline":
        """Group items by field or key function, with optional aggregation."""
        new_steps = self._steps + [GroupByStep(field_name=field, key_fn=key, aggregate_fn=aggregate)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def aggregate(self, **aggregations: Tuple[str, str]) -> "Pipeline":
        """Aggregate with functions: field=("source", "sum|avg|min|max|count")"""
        new_steps = self._steps + [AggregateStep(aggregations)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def flatten(self) -> "Pipeline":
        """Flatten nested lists (monad join)."""
        new_steps = self._steps + [FlattenStep()]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def unique(self, key: Optional[Callable[[Any], Any]] = None) -> "Pipeline":
        """Remove duplicates."""
        new_steps = self._steps + [UniqueStep(key)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def tap(self, fn: Callable[[Any], Any]) -> "Pipeline":
        """Execute a side effect function and pass through data unchanged."""
        new_steps = self._steps + [TapStep(fn)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def render(self, format: str, renderer: Callable[[Any, str], Any]) -> "Pipeline":
        """Render data into a formatted output."""
        new_steps = self._steps + [RenderStep(format, renderer)]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def emit(self, key: str) -> "Pipeline":
        """Set the output key for the result."""
        return Pipeline(_source=self._source, _steps=self._steps, _emit_key=key)

    # -------------------------------------------------------------------------
    # Operator Overloads
    # -------------------------------------------------------------------------

    def __rshift__(self, step: Step) -> "Pipeline":
        """Syntactic sugar: pipeline >> step"""
        new_steps = self._steps + [step]
        return Pipeline(_source=self._source, _steps=new_steps, _emit_key=self._emit_key)

    def __or__(self, step: Step) -> "Pipeline":
        """Alternative syntax: pipeline | step"""
        return self >> step

    # -------------------------------------------------------------------------
    # Execution
    # -------------------------------------------------------------------------

    def run(self, ctx: Context) -> PipelineResult[T]:
        """
        Execute the pipeline and return Result.

        This is where the lazy pipeline is evaluated.
        Errors short-circuit using Result monad semantics.
        """
        # Execute source
        source_result = self._source.execute(ctx)
        if source_result.is_err():
            return source_result

        # Run through steps using monadic bind
        current = source_result.unwrap()
        for step in self._steps:
            result = step.execute(current, ctx)
            if result.is_err():
                return result
            current = result.unwrap()

        return pipeline_ok(current)

    def execute(self, ctx: Context) -> Dict[str, Any]:
        """Execute and return formatted output dict."""
        result = self.run(ctx)

        if result.is_err():
            return {
                "success": False,
                "error": str(result.error) if hasattr(result, 'error') else str(result)
            }

        data = result.unwrap()
        output = {"success": True}

        if self._emit_key:
            output[self._emit_key] = data
            if isinstance(data, list):
                output["count"] = len(data)
        else:
            if isinstance(data, dict):
                output.update(data)
            elif isinstance(data, list):
                output["results"] = data
                output["count"] = len(data)
            else:
                output["result"] = data

        return output


class BoundPipeline(Generic[T, U]):
    """
    A pipeline created by monadic bind.

    This represents the composition of a pipeline with a function
    that produces another pipeline.
    """
    def __init__(self, source_pipeline: Pipeline[T], continuation: Callable[[T], Pipeline[U]]):
        self.source_pipeline = source_pipeline
        self.continuation = continuation
        self._emit_key: Optional[str] = None

    @classmethod
    def pure(cls, value: V) -> "Pipeline[V]":
        """Lift a value into a pipeline."""
        return Pipeline.pure(value)

    def bind(self, f: Callable[[U], "Pipeline[V]"]) -> "BoundPipeline[U, V]":
        """Chain another bind."""
        return BoundPipeline(self, f)  # type: ignore

    def run(self, ctx: Context) -> PipelineResult[U]:
        """Execute the bound pipeline."""
        # First run the source pipeline
        result = self.source_pipeline.run(ctx)
        if result.is_err():
            return result

        # Apply continuation to get next pipeline
        next_pipeline = self.continuation(result.unwrap())

        # Run the next pipeline
        return next_pipeline.run(ctx)

    def execute(self, ctx: Context) -> Dict[str, Any]:
        """Execute and return formatted output dict."""
        result = self.run(ctx)

        if result.is_err():
            return {
                "success": False,
                "error": str(result.error) if hasattr(result, 'error') else str(result)
            }

        data = result.unwrap()
        output = {"success": True}

        if self._emit_key:
            output[self._emit_key] = data
            if isinstance(data, list):
                output["count"] = len(data)
        else:
            if isinstance(data, dict):
                output.update(data)
            elif isinstance(data, list):
                output["results"] = data
                output["count"] = len(data)
            else:
                output["result"] = data

        return output


# =============================================================================
# Tool Specification Types
# =============================================================================

class ToolType(Enum):
    """Type of CADSL tool."""
    QUERY = "query"
    DETECTOR = "detector"
    DIAGRAM = "diagram"


@dataclass
class ParamSpec:
    """Specification for a tool parameter."""
    name: str
    type: type
    required: bool = True
    default: Any = None
    description: str = ""
    choices: Optional[List[Any]] = None

    def validate(self, value: Any) -> PipelineResult[Any]:
        """Validate a parameter value using Result monad."""
        if value is None:
            # If a default is provided, use it regardless of required flag
            if self.default is not None:
                return pipeline_ok(self.default)
            # Only error if required and no default
            if self.required:
                return pipeline_err("param", f"Required parameter '{self.name}' not provided")
            return pipeline_ok(self.default)

        if self.choices and value not in self.choices:
            return pipeline_err("param", f"Parameter '{self.name}' must be one of {self.choices}")

        try:
            # Type coercion
            if self.type == bool:
                if isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes")
                else:
                    value = bool(value)
            elif self.type == int:
                value = int(value)
            elif self.type == float:
                value = float(value)
            elif self.type == str:
                value = str(value)

            return pipeline_ok(value)
        except (ValueError, TypeError) as e:
            return pipeline_err("param", f"Invalid type for '{self.name}': {e}")


@dataclass
class ToolSpec:
    """Specification for a CADSL tool."""
    name: str
    type: ToolType
    description: str
    pipeline_factory: Callable[[Context], Pipeline]
    params: Dict[str, ParamSpec] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Tool Type Classes
# =============================================================================

class Query:
    """
    A read-only code inspection tool (functor over code data).

    Queries do not modify state - they only retrieve and transform data.
    """

    def __init__(self, spec: ToolSpec):
        self.spec = spec

    def execute(self, ctx: Context) -> Dict[str, Any]:
        """Execute the query and return results."""
        pipeline = self.spec.pipeline_factory(ctx)
        return pipeline.execute(ctx)


class Detector:
    """
    A code smell/pattern detector that creates findings.

    Detectors analyze code and produce findings with severity levels.
    """

    def __init__(self, spec: ToolSpec):
        self.spec = spec

    def execute(self, ctx: Context) -> Dict[str, Any]:
        """Execute the detector and return findings."""
        pipeline = self.spec.pipeline_factory(ctx)
        result = pipeline.execute(ctx)

        # Add detector metadata
        result["detector"] = self.spec.name
        result["category"] = self.spec.meta.get("category", "general")
        result["severity"] = self.spec.meta.get("severity", "medium")

        return result


class Diagram:
    """
    A visualization generator (transforms code structure to visual format).
    """

    def __init__(self, spec: ToolSpec):
        self.spec = spec

    def execute(self, ctx: Context) -> Dict[str, Any]:
        """Execute the diagram generator and return visualization."""
        pipeline = self.spec.pipeline_factory(ctx)
        result = pipeline.execute(ctx)

        result["format"] = ctx.params.get("format", "mermaid")
        return result


# =============================================================================
# Builder Functions (for DSL convenience)
# =============================================================================

def reql(query: str) -> Pipeline:
    """Create a pipeline from REQL query."""
    return Pipeline.from_reql(query)


def rag(query: str, top_k: int = 10,
        entity_types: Optional[List[str]] = None) -> Pipeline:
    """Create a pipeline from RAG semantic search."""
    return Pipeline.from_rag(query, top_k, entity_types)


def value(data: Any) -> Pipeline:
    """Create a pipeline from a literal value."""
    return Pipeline.from_value(data)

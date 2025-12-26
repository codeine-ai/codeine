"""
CADSL Transformer - AST to Pipeline Transformer.

This module transforms CADSL Lark parse trees into executable Pipeline objects
that can be run against a RETER instance.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field

from lark import Tree, Token

from .compiler import (
    compile_condition,
    compile_expression,
    compile_object_expr,
    ExpressionCompiler,
    ConditionCompiler,
    ObjectExprCompiler,
)


# ============================================================
# TOOL SPECIFICATION
# ============================================================

@dataclass
class ParamSpec:
    """Specification for a tool parameter."""
    name: str
    type: str
    required: bool = False
    default: Any = None
    choices: Optional[List[Any]] = None


@dataclass
class ToolSpec:
    """
    Specification for a CADSL tool.

    Contains all the information needed to create and execute a pipeline.
    """
    name: str
    tool_type: str  # "query", "detector", "diagram"
    description: str = ""
    params: List[ParamSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Pipeline components
    source_type: str = ""  # "reql", "rag", "value"
    source_content: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    emit_key: Optional[str] = None

    # For RAG source
    rag_query: Optional[str] = None
    rag_top_k: int = 10


# ============================================================
# TRANSFORMER
# ============================================================

class CADSLTransformer:
    """
    Transforms CADSL parse trees into ToolSpec objects.

    The ToolSpec can then be converted to executable Pipeline objects.
    """

    def __init__(self):
        self.expr_compiler = ExpressionCompiler()
        self.cond_compiler = ConditionCompiler()
        self.obj_compiler = ObjectExprCompiler()

    def transform(self, tree: Tree) -> List[ToolSpec]:
        """
        Transform a parse tree into a list of ToolSpec objects.

        Args:
            tree: Lark parse tree from CADSLParser

        Returns:
            List of ToolSpec objects
        """
        tools = []

        for child in tree.children:
            if isinstance(child, Tree) and child.data == "tool_def":
                spec = self._transform_tool_def(child)
                if spec:
                    tools.append(spec)

        return tools

    def _transform_tool_def(self, node: Tree) -> Optional[ToolSpec]:
        """Transform a tool_def node into a ToolSpec."""
        # Extract tool type
        tool_type = self._get_tool_type(node)
        tool_name = self._get_tool_name(node)

        spec = ToolSpec(
            name=tool_name,
            tool_type=tool_type,
        )

        # Extract metadata
        metadata_node = self._find_child(node, "metadata")
        if metadata_node:
            spec.metadata = self._transform_metadata(metadata_node)

        # Extract tool body
        tool_body = self._find_child(node, "tool_body")
        if tool_body:
            # Extract docstring
            docstring_node = self._find_child(tool_body, "docstring")
            if docstring_node:
                spec.description = self._extract_docstring(docstring_node)

            # Extract parameters
            for child in tool_body.children:
                if isinstance(child, Tree) and child.data == "param_def":
                    param = self._transform_param_def(child)
                    if param:
                        spec.params.append(param)

            # Extract pipeline
            pipeline = self._find_child(tool_body, "pipeline")
            if pipeline:
                self._transform_pipeline(pipeline, spec)

        return spec

    def _get_tool_type(self, node: Tree) -> str:
        """Extract tool type from tool_def node."""
        for child in node.children:
            if isinstance(child, Tree):
                if child.data == "tool_query":
                    return "query"
                elif child.data == "tool_detector":
                    return "detector"
                elif child.data == "tool_diagram":
                    return "diagram"
        return "query"

    def _get_tool_name(self, node: Tree) -> str:
        """Extract tool name from tool_def node."""
        for child in node.children:
            if isinstance(child, Token) and child.type == "NAME":
                return str(child)
        return "unnamed"

    def _find_child(self, node: Tree, data: str) -> Optional[Tree]:
        """Find first child with matching data."""
        for child in node.children:
            if isinstance(child, Tree) and child.data == data:
                return child
        return None

    # --------------------------------------------------------
    # Metadata
    # --------------------------------------------------------

    def _transform_metadata(self, node: Tree) -> Dict[str, Any]:
        """Transform metadata node to dict."""
        metadata = {}

        for child in node.children:
            if isinstance(child, Tree) and child.data == "meta_item":
                key = None
                value = None

                for item in child.children:
                    if isinstance(item, Token) and item.type == "NAME":
                        key = str(item)
                    elif isinstance(item, Tree) and item.data == "meta_value":
                        value = self._extract_meta_value(item)

                if key:
                    metadata[key] = value

        return metadata

    def _extract_meta_value(self, node: Tree) -> Any:
        """Extract value from meta_value node."""
        for child in node.children:
            if isinstance(child, Token):
                if child.type == "STRING":
                    return self._unquote(str(child))
                elif child.type == "NAME":
                    return str(child)
            elif isinstance(child, Tree):
                if child.data == "capability_array":
                    return self._extract_capability_list(child)
        return None

    def _extract_capability_list(self, node: Tree) -> List[str]:
        """Extract capability list."""
        caps = []
        for child in node.children:
            if isinstance(child, Tree) and child.data == "capability_list":
                for item in child.children:
                    if isinstance(item, Token) and item.type == "STRING":
                        caps.append(self._unquote(str(item)))
        return caps

    # --------------------------------------------------------
    # Parameters
    # --------------------------------------------------------

    def _transform_param_def(self, node: Tree) -> Optional[ParamSpec]:
        """Transform param_def node to ParamSpec."""
        name = None
        param_type = "str"
        default = None
        required = False
        choices = None

        for child in node.children:
            if isinstance(child, Token) and child.type == "NAME":
                name = str(child)
            elif isinstance(child, Tree):
                if child.data.startswith("type_"):
                    param_type = self._extract_type(child)
                elif child.data == "param_modifiers":
                    for mod in child.children:
                        if isinstance(mod, Tree):
                            if mod.data == "param_default":
                                default = self._extract_value(mod)
                            elif mod.data == "param_required":
                                required = True
                            elif mod.data == "param_choices":
                                choices = self._extract_choices(mod)

        if name:
            return ParamSpec(
                name=name,
                type=param_type,
                required=required,
                default=default,
                choices=choices,
            )
        return None

    def _extract_type(self, node: Tree) -> str:
        """Extract type name from type_spec node."""
        type_map = {
            "type_int": "int",
            "type_str": "str",
            "type_float": "float",
            "type_bool": "bool",
            "type_list": "list",
        }
        if node.data in type_map:
            return type_map[node.data]
        if node.data == "type_list_of":
            inner = None
            for child in node.children:
                if isinstance(child, Tree) and child.data.startswith("type_"):
                    inner = self._extract_type(child)
            return f"list<{inner}>" if inner else "list"
        return "str"

    def _extract_choices(self, node: Tree) -> List[Any]:
        """Extract choices from param_choices node."""
        choices = []
        for child in node.children:
            if isinstance(child, Tree) and child.data == "value_list":
                for item in child.children:
                    val = self._extract_value(item)
                    if val is not None:
                        choices.append(val)
        return choices

    # --------------------------------------------------------
    # Pipeline
    # --------------------------------------------------------

    def _transform_pipeline(self, node: Tree, spec: ToolSpec) -> None:
        """Transform pipeline node and update spec."""
        for child in node.children:
            if isinstance(child, Tree):
                if child.data == "source":
                    # Source wrapper
                    for source_child in child.children:
                        if isinstance(source_child, Tree):
                            self._transform_source(source_child, spec)

                elif child.data in ("reql_source", "rag_source", "value_source"):
                    self._transform_source(child, spec)

                elif child.data == "step":
                    # Step wrapper
                    for step_child in child.children:
                        if isinstance(step_child, Tree):
                            step = self._transform_step(step_child)
                            if step:
                                spec.steps.append(step)

                elif child.data.endswith("_step"):
                    step = self._transform_step(child)
                    if step:
                        spec.steps.append(step)

    def _transform_source(self, node: Tree, spec: ToolSpec) -> None:
        """Transform source node and update spec."""
        if node.data == "reql_source":
            spec.source_type = "reql"
            # Extract REQL content from REQL_BLOCK token
            for child in node.children:
                if isinstance(child, Token) and child.type == "REQL_BLOCK":
                    content = str(child)
                    # Remove outer braces
                    if content.startswith("{") and content.endswith("}"):
                        content = content[1:-1].strip()
                    spec.source_content = content

        elif node.data == "rag_source":
            spec.source_type = "rag"
            # Extract query and top_k from rag_args
            for child in node.children:
                if isinstance(child, Tree) and child.data == "rag_args":
                    for arg in child.children:
                        if isinstance(arg, Tree):
                            # Query expression
                            spec.rag_query = self._extract_expr_as_string(arg)
                        elif isinstance(arg, Token) and arg.type == "INT":
                            spec.rag_top_k = int(str(arg))

        elif node.data == "value_source":
            spec.source_type = "value"
            # Extract value expression
            for child in node.children:
                if isinstance(child, Tree):
                    spec.source_content = self._extract_expr_as_string(child)

    def _transform_step(self, node: Tree) -> Optional[Dict[str, Any]]:
        """Transform a step node to a step specification dict."""
        step_type = node.data.replace("_step", "")

        if step_type == "filter":
            return self._transform_filter_step(node)
        elif step_type == "select":
            return self._transform_select_step(node)
        elif step_type == "map":
            return self._transform_map_step(node)
        elif step_type == "flat_map":
            return self._transform_flat_map_step(node)
        elif step_type == "order_by":
            return self._transform_order_by_step(node)
        elif step_type == "limit":
            return self._transform_limit_step(node)
        elif step_type == "offset":
            return self._transform_offset_step(node)
        elif step_type == "group_by":
            return self._transform_group_by_step(node)
        elif step_type == "aggregate":
            return self._transform_aggregate_step(node)
        elif step_type == "unique":
            return self._transform_unique_step(node)
        elif step_type == "flatten":
            return {"type": "flatten"}
        elif step_type == "tap":
            return self._transform_tap_step(node)
        elif step_type == "python":
            return self._transform_python_step(node)
        elif step_type == "render":
            return self._transform_render_step(node)
        elif step_type == "emit":
            return self._transform_emit_step(node)

        return None

    def _transform_filter_step(self, node: Tree) -> Dict[str, Any]:
        """Transform filter step."""
        # Find condition
        for child in node.children:
            if isinstance(child, Tree):
                predicate = compile_condition(child)
                return {
                    "type": "filter",
                    "predicate": predicate,
                    "_condition_node": child,  # For debugging
                }
        return {"type": "filter", "predicate": lambda r, ctx=None: True}

    def _transform_select_step(self, node: Tree) -> Dict[str, Any]:
        """Transform select step."""
        fields = {}  # output_name -> source_name

        field_list = self._find_child(node, "field_list")
        if field_list:
            for item in field_list.children:
                if isinstance(item, Tree):
                    if item.data == "field_simple":
                        name = str(item.children[0])
                        fields[name] = name
                    elif item.data == "field_alias":
                        source = str(item.children[0])
                        alias = str(item.children[1])
                        fields[alias] = source
                    elif item.data == "field_rename":
                        alias = str(item.children[0])
                        source = str(item.children[1])
                        fields[alias] = source

        return {"type": "select", "fields": fields}

    def _transform_map_step(self, node: Tree) -> Dict[str, Any]:
        """Transform map step."""
        # Find object expression
        obj_expr = self._find_child(node, "object_expr")
        if obj_expr:
            transform = compile_object_expr(obj_expr)
            return {"type": "map", "transform": transform}

        return {"type": "map", "transform": lambda r, ctx=None: r}

    def _transform_flat_map_step(self, node: Tree) -> Dict[str, Any]:
        """Transform flat_map step."""
        for child in node.children:
            if isinstance(child, Tree):
                expr = compile_expression(child)
                return {"type": "flat_map", "transform": expr}

        return {"type": "flat_map", "transform": lambda r, ctx=None: [r]}

    def _transform_order_by_step(self, node: Tree) -> Dict[str, Any]:
        """Transform order_by step."""
        orders = []

        for child in node.children:
            if isinstance(child, Tree):
                if child.data == "order_desc":
                    field = str(child.children[0])
                    orders.append(("-" + field, True))
                elif child.data == "order_asc":
                    field = str(child.children[0])
                    orders.append((field, False))
                elif child.data == "order_asc_default":
                    field = str(child.children[0])
                    orders.append((field, False))

        return {"type": "order_by", "orders": orders}

    def _transform_limit_step(self, node: Tree) -> Dict[str, Any]:
        """Transform limit step."""
        for child in node.children:
            if isinstance(child, Tree) and child.data == "limit_value":
                return self._extract_limit_value(child, "limit")
            elif isinstance(child, Token) and child.type == "INT":
                return {"type": "limit", "count": int(str(child))}

        return {"type": "limit", "count": 100}

    def _transform_offset_step(self, node: Tree) -> Dict[str, Any]:
        """Transform offset step."""
        for child in node.children:
            if isinstance(child, Tree) and child.data == "offset_value":
                return self._extract_limit_value(child, "offset")
            elif isinstance(child, Token) and child.type == "INT":
                return {"type": "offset", "count": int(str(child))}

        return {"type": "offset", "count": 0}

    def _extract_limit_value(self, node: Tree, step_type: str) -> Dict[str, Any]:
        """Extract limit/offset value (may be param ref or int)."""
        for child in node.children:
            if isinstance(child, Token) and child.type == "INT":
                return {"type": step_type, "count": int(str(child))}
            elif isinstance(child, Tree) and child.data == "param_ref":
                param = str(child.children[0])
                return {"type": step_type, "param": param}

        return {"type": step_type, "count": 100 if step_type == "limit" else 0}

    def _transform_group_by_step(self, node: Tree) -> Dict[str, Any]:
        """Transform group_by step."""
        group_spec = self._find_child(node, "group_spec")
        if not group_spec:
            return {"type": "group_by", "field": None}

        result = {"type": "group_by", "field": None, "aggregate": None}

        for child in group_spec.children:
            if isinstance(child, Tree):
                if child.data == "group_field":
                    result["field"] = str(child.children[0])
                elif child.data == "group_lambda":
                    # key: row => expr
                    lambda_expr = self._find_child(child, "lambda_expr")
                    if lambda_expr:
                        expr = lambda_expr.children[-1]  # Expression after =>
                        result["key_fn"] = compile_expression(expr)
                elif child.data == "group_all":
                    result["field"] = "_all"
                elif child.data in ("agg_func_ref", "agg_inline"):
                    result["aggregate"] = self._extract_aggregate(child)

        return result

    def _extract_aggregate(self, node: Tree) -> Dict[str, Tuple[str, str]]:
        """Extract aggregate specification."""
        aggs = {}

        if node.data == "agg_func_ref":
            # Just a function name reference
            return {"_ref": str(node.children[0])}

        # Inline aggregation: {field: op(source), ...}
        for child in node.children:
            if isinstance(child, Tree) and child.data == "agg_field_list":
                for agg_field in child.children:
                    if isinstance(agg_field, Tree) and agg_field.data == "agg_field":
                        out_name = str(agg_field.children[0])
                        op_node = agg_field.children[1]
                        source = str(agg_field.children[2])
                        op = op_node.data.replace("agg_", "")
                        aggs[out_name] = (source, op)

        return aggs

    def _transform_aggregate_step(self, node: Tree) -> Dict[str, Any]:
        """Transform aggregate step."""
        aggs = {}

        for child in node.children:
            if isinstance(child, Tree) and child.data == "agg_field":
                out_name = str(child.children[0])
                op_node = child.children[1]
                source = str(child.children[2])
                op = op_node.data.replace("agg_", "")
                aggs[out_name] = (source, op)

        return {"type": "aggregate", "aggregations": aggs}

    def _transform_unique_step(self, node: Tree) -> Dict[str, Any]:
        """Transform unique step."""
        key = None
        for child in node.children:
            if isinstance(child, Token) and child.type == "NAME":
                key = str(child)

        if key:
            return {"type": "unique", "key": lambda r, k=key: r.get(k) if isinstance(r, dict) else r}
        return {"type": "unique", "key": None}

    def _transform_tap_step(self, node: Tree) -> Dict[str, Any]:
        """Transform tap step."""
        func_name = None
        for child in node.children:
            if isinstance(child, Token) and child.type == "NAME":
                func_name = str(child)

        return {"type": "tap", "func_name": func_name}

    def _transform_python_step(self, node: Tree) -> Dict[str, Any]:
        """Transform python step."""
        code = ""
        for child in node.children:
            if isinstance(child, Token) and child.type == "PYTHON_BLOCK":
                content = str(child)
                # Remove outer braces
                if content.startswith("{") and content.endswith("}"):
                    code = content[1:-1]

        return {"type": "python", "code": code}

    def _transform_render_step(self, node: Tree) -> Dict[str, Any]:
        """Transform render step."""
        render_spec = self._find_child(node, "render_spec")
        if not render_spec:
            return {"type": "render", "format": "text", "renderer": None}

        result = {"type": "render", "format": "text", "renderer": None}

        for child in render_spec.children:
            if isinstance(child, Tree):
                if child.data == "render_with_format":
                    # format: "x", renderer: name
                    for item in child.children:
                        if isinstance(item, Tree) and item.data == "format_value":
                            for fmt in item.children:
                                if isinstance(fmt, Token) and fmt.type == "STRING":
                                    result["format"] = self._unquote(str(fmt))
                                elif isinstance(fmt, Tree) and fmt.data == "param_ref":
                                    result["format_param"] = str(fmt.children[0])
                        elif isinstance(item, Token) and item.type == "NAME":
                            result["renderer"] = str(item)

                elif child.data == "render_func":
                    result["renderer"] = str(child.children[0])

        return result

    def _transform_emit_step(self, node: Tree) -> Dict[str, Any]:
        """Transform emit step."""
        key = "result"
        for child in node.children:
            if isinstance(child, Token) and child.type == "NAME":
                key = str(child)

        return {"type": "emit", "key": key}

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _extract_docstring(self, node: Tree) -> str:
        """Extract docstring text."""
        for child in node.children:
            if isinstance(child, Token) and child.type == "TRIPLE_STRING":
                text = str(child)
                # Remove triple quotes
                if text.startswith('"""') and text.endswith('"""'):
                    return text[3:-3].strip()
        return ""

    def _extract_value(self, node: Tree) -> Any:
        """Extract a value from a value node."""
        if isinstance(node, Token):
            return self._token_to_value(node)

        for child in node.children:
            if isinstance(child, Token):
                return self._token_to_value(child)
            elif isinstance(child, Tree):
                if child.data == "val_string":
                    return self._unquote(str(child.children[0]))
                elif child.data == "val_int":
                    return int(str(child.children[0]))
                elif child.data == "val_float":
                    return float(str(child.children[0]))
                elif child.data == "val_true":
                    return True
                elif child.data == "val_false":
                    return False
                elif child.data == "val_null":
                    return None
                else:
                    return self._extract_value(child)

        return None

    def _token_to_value(self, token: Token) -> Any:
        """Convert token to Python value."""
        if token.type == "STRING":
            return self._unquote(str(token))
        elif token.type in ("SIGNED_INT", "INT"):
            return int(str(token))
        elif token.type in ("SIGNED_FLOAT", "FLOAT"):
            return float(str(token))
        return str(token)

    def _extract_expr_as_string(self, node: Tree) -> str:
        """Extract expression as string representation."""
        if isinstance(node, Token):
            if node.type == "STRING":
                return self._unquote(str(node))
            return str(node)

        # For complex expressions, return a placeholder
        return "{expr}"

    def _unquote(self, s: str) -> str:
        """Remove quotes from a string."""
        if len(s) >= 2:
            if (s.startswith('"') and s.endswith('"')) or \
               (s.startswith("'") and s.endswith("'")):
                return s[1:-1]
        return s


# ============================================================
# PIPELINE BUILDER
# ============================================================

class PipelineBuilder:
    """
    Builds executable Pipeline objects from ToolSpec.

    This separates the AST transformation from Pipeline construction,
    allowing for different target Pipeline implementations.
    """

    def __init__(self):
        pass

    def build(self, spec: ToolSpec) -> Callable:
        """
        Build a pipeline factory from a ToolSpec.

        Args:
            spec: ToolSpec from CADSLTransformer

        Returns:
            A callable that creates a Pipeline when given a Context
        """
        # Import here to avoid circular imports
        from codeine.dsl.core import (
            Pipeline, REQLSource, RAGSource, ValueSource,
            FilterStep, SelectStep, MapStep, FlatMapStep,
            OrderByStep, LimitStep, OffsetStep,
            GroupByStep, AggregateStep, FlattenStep, UniqueStep,
            TapStep, RenderStep,
        )

        def pipeline_factory(ctx):
            # Create source
            if spec.source_type == "reql":
                pipeline = Pipeline(_source=REQLSource(spec.source_content))
            elif spec.source_type == "rag":
                pipeline = Pipeline(_source=RAGSource(
                    query=spec.rag_query or "",
                    top_k=spec.rag_top_k,
                ))
            elif spec.source_type == "value":
                pipeline = Pipeline(_source=ValueSource(spec.source_content))
            else:
                pipeline = Pipeline(_source=ValueSource([]))

            # Add steps
            emit_key = None
            for step_spec in spec.steps:
                step_type = step_spec.get("type")

                if step_type == "filter":
                    predicate = step_spec.get("predicate", lambda r, ctx=None: True)
                    pipeline = pipeline.filter(predicate)

                elif step_type == "select":
                    fields = step_spec.get("fields", {})
                    pipeline = pipeline >> SelectStep(fields)

                elif step_type == "map":
                    transform = step_spec.get("transform", lambda r, ctx=None: r)
                    pipeline = pipeline.map(transform)

                elif step_type == "flat_map":
                    transform = step_spec.get("transform", lambda r, ctx=None: [r])
                    pipeline = pipeline.flat_map(transform)

                elif step_type == "order_by":
                    orders = step_spec.get("orders", [])
                    for field, desc in orders:
                        if desc:
                            pipeline = pipeline.order_by("-" + field.lstrip("-"))
                        else:
                            pipeline = pipeline.order_by(field)

                elif step_type == "limit":
                    if "param" in step_spec:
                        param = step_spec["param"]
                        count = ctx.params.get(param, 100)
                    else:
                        count = step_spec.get("count", 100)
                    pipeline = pipeline.limit(count)

                elif step_type == "offset":
                    if "param" in step_spec:
                        param = step_spec["param"]
                        count = ctx.params.get(param, 0)
                    else:
                        count = step_spec.get("count", 0)
                    pipeline = pipeline.offset(count)

                elif step_type == "group_by":
                    field = step_spec.get("field")
                    key_fn = step_spec.get("key_fn")
                    agg = step_spec.get("aggregate")
                    pipeline = pipeline.group_by(field=field, key=key_fn)

                elif step_type == "aggregate":
                    aggs = step_spec.get("aggregations", {})
                    pipeline = pipeline >> AggregateStep(aggs)

                elif step_type == "flatten":
                    pipeline = pipeline.flatten()

                elif step_type == "unique":
                    key = step_spec.get("key")
                    pipeline = pipeline.unique(key)

                elif step_type == "python":
                    code = step_spec.get("code", "result = rows")
                    pipeline = pipeline >> PythonStep(code)

                elif step_type == "render":
                    fmt = step_spec.get("format", "text")
                    if "format_param" in step_spec:
                        fmt = ctx.params.get(step_spec["format_param"], fmt)
                    renderer_name = step_spec.get("renderer")
                    renderer = get_renderer(renderer_name) if renderer_name else default_renderer
                    pipeline = pipeline.render(fmt, renderer)

                elif step_type == "emit":
                    emit_key = step_spec.get("key", "result")

            if emit_key:
                pipeline = pipeline.emit(emit_key)

            return pipeline

        return pipeline_factory


# ============================================================
# PYTHON STEP
# ============================================================

class PythonStep:
    """
    Executes inline Python code as a pipeline step.

    Available in the Python block:
    - rows: Input data from previous step
    - ctx: Execution context with params
    - result: Must be set to the output value
    """

    def __init__(self, code: str):
        self.code = code
        try:
            self.compiled = compile(code, "<cadsl_python>", "exec")
        except SyntaxError as e:
            self.compiled = None
            self.error = str(e)

    def execute(self, data, ctx=None):
        """Execute the Python code."""
        from codeine.dsl.core import pipeline_ok, pipeline_err

        if self.compiled is None:
            return pipeline_err("python", f"Python syntax error: {self.error}")

        # Create execution namespace
        namespace = {
            "rows": data,
            "ctx": ctx,
            "result": None,
            # Common imports
            "defaultdict": __import__("collections").defaultdict,
            "Counter": __import__("collections").Counter,
            "re": __import__("re"),
            "json": __import__("json"),
            "math": __import__("math"),
        }

        try:
            exec(self.compiled, namespace)

            if namespace.get("result") is None:
                # If no result set, use rows
                return pipeline_ok(data)

            return pipeline_ok(namespace["result"])
        except Exception as e:
            return pipeline_err("python", f"Python execution error: {e}", e)


# ============================================================
# RENDERERS
# ============================================================

def default_renderer(data: Any, format: str) -> str:
    """Default renderer - converts to string."""
    import json
    if format == "json":
        return json.dumps(data, indent=2, default=str)
    elif format == "markdown":
        if isinstance(data, list):
            return "\n".join(f"- {item}" for item in data)
        return str(data)
    return str(data)


def get_renderer(name: str) -> Callable:
    """Get a renderer by name."""
    renderers = {
        "json": lambda d, f: __import__("json").dumps(d, indent=2, default=str),
        "text": lambda d, f: str(d),
        "markdown": default_renderer,
    }
    return renderers.get(name, default_renderer)


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def transform_cadsl(tree) -> List[ToolSpec]:
    """Transform a parse tree into ToolSpec objects."""
    transformer = CADSLTransformer()
    return transformer.transform(tree)


def build_pipeline(spec: ToolSpec) -> Callable:
    """Build a pipeline factory from a ToolSpec."""
    builder = PipelineBuilder()
    return builder.build(spec)

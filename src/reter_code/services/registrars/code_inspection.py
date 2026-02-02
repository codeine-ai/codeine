"""
Code Inspection Tools Registrar

Consolidates code analysis tools into a single code_inspection MCP tool.
All operations go through ReterClient via ZeroMQ (remote-only mode).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from fastmcp import FastMCP
from .base import ToolRegistrarBase, truncate_mcp_response

if TYPE_CHECKING:
    from ...server.reter_client import ReterClient


class CodeInspectionToolsRegistrar(ToolRegistrarBase):
    """
    Registers a unified code_inspection tool with FastMCP.

    All operations go through ReterClient via ZeroMQ.

    ::: This is-in-layer Service-Layer.
    ::: This is a registrar.
    ::: This is-in-process MCP-Server-Process.
    ::: This is stateless.
    """

    def __init__(
        self,
        instance_manager,
        persistence_service,
        tools_filter=None,
        reter_client: Optional["ReterClient"] = None
    ):
        super().__init__(instance_manager, persistence_service, tools_filter, reter_client)

    def register(self, app: FastMCP) -> None:
        """Register the code_inspection tool (respects tools_filter)."""
        if not self._should_register("code_inspection"):
            return

        registrar = self

        @app.tool()
        @truncate_mcp_response
        def code_inspection(
            action: str,
            target: Optional[str] = None,
            module: Optional[str] = None,
            limit: int = 100,
            offset: int = 0,
            format: str = "json",
            include_methods: bool = True,
            include_attributes: bool = True,
            include_docstrings: bool = True,
            summary_only: bool = False,
            params: Optional[Dict[str, Any]] = None,
        ) -> Dict[str, Any]:
            """
            Unified code inspection tool for Python analysis.

            **See: python://reter/tools for complete documentation**

            For UML diagrams, use the 'diagram' tool instead.

            Args:
                action: The operation to perform. Available actions:

                    **Structure/Navigation:**
                    - list_modules: List all Python modules in the codebase.
                    - list_classes: List all classes, optionally filtered by module.
                    - list_functions: List top-level functions, optionally filtered by module.
                    - describe_class: Get detailed class description with methods/attributes.
                    - get_docstring: Get the docstring of a class, method, or function.
                    - get_method_signature: Get method signature with parameters and return type.
                    - get_class_hierarchy: Get inheritance hierarchy (parents and children).
                    - get_package_structure: Get package/module directory structure.

                    **Search/Find:**
                    - find_usages: Find where a class/method/function is called.
                    - find_subclasses: Find all subclasses of a class.
                    - find_callers: Find all callers of a function/method.
                    - find_callees: Find all functions/methods called by target.
                    - find_decorators: Find all decorator usages.
                    - find_tests: Find tests for a module, class, or function.

                    **Analysis:**
                    - analyze_dependencies: Analyze module dependency graph.
                    - get_imports: Get complete module import dependency graph.
                    - get_external_deps: Get external package dependencies.
                    - predict_impact: Predict impact of changing a function/method/class.
                    - get_complexity: Calculate complexity metrics.
                    - get_magic_methods: Find all dunder methods.
                    - get_interfaces: Find classes implementing interfaces.
                    - get_public_api: Get all public classes and functions.
                    - get_type_hints: Extract all type annotations.
                    - get_api_docs: Extract all API documentation.
                    - get_exceptions: Get exception class hierarchy.
                    - get_architecture: Generate architectural overview.

                target: Target entity name (class, method, function, decorator)
                module: Module name filter for list operations
                limit: Maximum results to return (default: 100)
                offset: Pagination offset (default: 0)
                format: Output format - "json", "markdown", or "mermaid" (default: "json")
                include_methods: Include methods in class descriptions (default: True)
                include_attributes: Include attributes in class descriptions (default: True)
                include_docstrings: Include docstrings (default: True)
                summary_only: Return summary only for smaller response (default: False)
                params: Additional action-specific parameters as dict

            Returns:
                Action-specific results with success status
            """
            if registrar.reter_client is None:
                return {
                    "success": False,
                    "error": "RETER server not connected",
                    "action": action,
                }

            try:
                kwargs = {
                    "action": action,
                    "target": target,
                    "module": module,
                    "limit": limit,
                    "offset": offset,
                    "format": format,
                    "include_methods": include_methods,
                    "include_attributes": include_attributes,
                    "include_docstrings": include_docstrings,
                    "summary_only": summary_only,
                }
                if params:
                    kwargs["params"] = params
                return registrar.reter_client.code_inspection(**kwargs)
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": action,
                }

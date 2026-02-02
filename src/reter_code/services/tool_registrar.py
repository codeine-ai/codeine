"""
Tool Registrar Service

Handles registration and management of MCP tools.
All RETER operations go through ReterClient via ZeroMQ (remote-only mode).
"""

import asyncio
import os
from typing import Dict, Any, Optional, TYPE_CHECKING, Set
from fastmcp import FastMCP, Context

from ..logging_config import nlq_debug_logger as debug_log, ensure_nlq_logger_configured
from .tools_service import ToolsRegistrar
from .registrars.system_tools import SystemToolsRegistrar
from .response_truncation import truncate_response
from .hybrid_query_engine import build_similar_tools_section
from .agent_sdk_client import (
    is_agent_sdk_available,
    generate_cadsl_query,
    retry_cadsl_query,
)
from ..server.reter_client import ReterClient

if TYPE_CHECKING:
    pass


# Default tools available in "default" mode
DEFAULT_TOOLS: Set[str] = {
    "reql",
    "system",
    "thinking",
    "session",
    "items",
    "execute_cadsl",
    "generate_cadsl",
    "semantic_search",
    "natural_language_query",
}


class ToolRegistrar:
    """
    Manages MCP tool registration.

    All RETER operations go through ReterClient via ZeroMQ.

    ::: This is-in-layer Service-Layer.
    ::: This is a model-context-protocol-tool-provider.
    ::: This depends-on `reter_code.server.ReterClient`.
    ::: This is-in-process MCP-Server-Process.
    ::: This is stateless.
    """

    def __init__(
        self,
        reter_ops,
        persistence,
        instance_manager,
        default_manager,
        reter_client: Optional[ReterClient] = None
    ):
        """
        Initialize ToolRegistrar.

        Args:
            reter_ops: Kept for interface compatibility
            persistence: Kept for interface compatibility
            instance_manager: Kept for interface compatibility
            default_manager: Kept for interface compatibility
            reter_client: ReterClient for remote RETER access via ZeroMQ
        """
        self.reter_client = reter_client

        # Read tools availability mode from environment
        self._tools_mode = os.environ.get("TOOLS_AVAILABLE", "default").lower()

        # Direct tools registration with reter_client
        tools_filter = DEFAULT_TOOLS if self._tools_mode == "default" else None
        self.tools_registrar = ToolsRegistrar(
            instance_manager, persistence, default_manager,
            tools_filter=tools_filter, reter_client=reter_client
        )

        # System tools registrar
        self.system_registrar = SystemToolsRegistrar(
            instance_manager, persistence, default_manager, reter_ops,
            reter_client=reter_client
        )

    def register_all_tools(self, app: FastMCP) -> None:
        """Register all MCP tools with the application."""
        import logging
        logger = logging.getLogger(__name__)

        is_full_mode = self._tools_mode == "full"

        if is_full_mode:
            logger.info("Tools mode: FULL (all tools available)")
        else:
            logger.info("Tools mode: DEFAULT (limited to: %s)", ", ".join(sorted(DEFAULT_TOOLS)))

        # Knowledge tools - full mode only
        if is_full_mode:
            self._register_knowledge_tools(app)

        # Query tools (reql)
        if is_full_mode or "reql" in DEFAULT_TOOLS:
            self._register_query_tools(app)

        # System tool
        if is_full_mode or "system" in DEFAULT_TOOLS:
            self.system_registrar.register(app)

        # Domain tools
        self._register_domain_tools(app)

        # Experimental tools
        self._register_experimental_tools(app, is_full_mode)

    def _register_knowledge_tools(self, app: FastMCP) -> None:
        """Register knowledge management tools."""
        registrar = self

        @app.tool()
        def add_knowledge(
            source: str,
            type: str = "ontology",
            source_id: Optional[str] = None,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Incrementally add knowledge to RETER's semantic memory.

            Args:
                source: Ontology content, file path, or code file path
                type: 'ontology', 'python', 'javascript', 'html', 'csharp', or 'cpp'
                source_id: Optional identifier for selective forgetting later

            Returns:
                success, items_added, execution_time_ms, source_id
            """
            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            try:
                return registrar.reter_client.add_knowledge(source, type, source_id)
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.tool()
        def add_external_directory(
            directory: str,
            recursive: bool = True,
            exclude_patterns: list[str] = None,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Load EXTERNAL code files from a directory.

            Args:
                directory: Path to directory containing code files
                recursive: Search subdirectories (default: True)
                exclude_patterns: Glob patterns to exclude

            Returns:
                success, files_loaded, total_files, total_wmes, errors
            """
            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            try:
                return registrar.reter_client.add_directory(directory, recursive, exclude_patterns)
            except Exception as e:
                return {"success": False, "error": str(e)}

        @app.tool()
        def validate_cnl(
            statement: str,
            context_entity: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Validate a CNL statement without adding it.

            Args:
                statement: CNL statement to validate
                context_entity: Entity name for "This" resolution

            Returns:
                success, errors, facts, resolved_statement
            """
            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            try:
                return registrar.reter_client.validate_cnl(statement, context_entity)
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _register_query_tools(self, app: FastMCP) -> None:
        """Register query execution tools."""
        registrar = self

        @app.tool()
        def reql(
            query: str,
            type: str = "reql"
        ) -> Dict[str, Any]:
            """
            Execute a REQL query against the code knowledge graph.

            Args:
                query: Query string in REQL syntax
                type: 'reql', 'dl', or 'pattern'

            Returns:
                results, count, source_validity, warnings
            """
            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            try:
                if type == "reql":
                    return truncate_response(registrar.reter_client.reql(query))
                elif type == "dl":
                    instances = registrar.reter_client.dl(query)
                    return truncate_response({"success": True, "instances": instances, "count": len(instances)})
                elif type == "pattern":
                    return truncate_response(registrar.reter_client.pattern(query))
                else:
                    return {"success": False, "error": f"Unknown query type: {type}"}
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _register_domain_tools(self, app: FastMCP) -> None:
        """Register all RETER domain-specific tools."""
        self.tools_registrar.register_all_tools(app)

    def _register_experimental_tools(self, app: FastMCP, is_full_mode: bool = True) -> None:
        """Register experimental tools."""
        if is_full_mode or "natural_language_query" in DEFAULT_TOOLS:
            self._register_nlq_tool(app)

        if is_full_mode or "execute_cadsl" in DEFAULT_TOOLS:
            self._register_cadsl_tool(app)

        if is_full_mode or "generate_cadsl" in DEFAULT_TOOLS:
            self._register_generate_cadsl_tool(app)

    def _execute_single_cadsl_pipeline(
        self,
        query: str,
        execution_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single CADSL query pipeline via ReterClient."""
        execution_state["attempts"] += execution_state.get("attempt_delta", 1)
        execution_state["tools_used"].extend(execution_state.get("tools_delta", []))

        # Auto-fix bare reql blocks
        fixed_query = self._fix_bare_reql_block(query)

        if self.reter_client is None:
            return self._cadsl_error_response(fixed_query, execution_state, "RETER server not connected")

        try:
            result = self.reter_client.execute_cadsl(fixed_query)
            result["cadsl_query"] = fixed_query
            result["query_type"] = "cadsl"
            result["attempts"] = execution_state["attempts"]
            result["tools_used"] = execution_state["tools_used"]
            return result
        except Exception as e:
            return self._cadsl_error_response(fixed_query, execution_state, str(e))

    def _cadsl_error_response(
        self,
        query: str,
        execution_state: Dict[str, Any],
        error: str
    ) -> Dict[str, Any]:
        """Build a standardized CADSL error response."""
        return {
            "success": False,
            "results": [],
            "count": 0,
            "cadsl_query": query,
            "query_type": "cadsl",
            "attempts": execution_state["attempts"],
            "tools_used": execution_state["tools_used"],
            "error": error
        }

    async def _execute_cadsl_query(
        self,
        question: str,
        max_retries: int,
        similar_tools: Optional[list] = None
    ) -> Dict[str, Any]:
        """Execute a CADSL query using Agent SDK for generation."""
        debug_log.debug(f"\n{'='*60}\nCADSL EXECUTION (Agent SDK)\n{'='*60}")

        if not is_agent_sdk_available():
            return {
                "success": False,
                "results": [],
                "count": 0,
                "query_type": "cadsl",
                "error": "Claude Agent SDK not available"
            }

        similar_tools_context = build_similar_tools_section(similar_tools) if similar_tools else None
        execution_state = {"attempts": 0, "tools_used": []}
        max_empty_retries = 2

        try:
            # Get schema info from server
            schema_info = "Schema information unavailable"
            if self.reter_client is not None:
                try:
                    status = self.reter_client.get_status()
                    schema_info = f"Codebase has {status.get('class_count', 0)} classes, {status.get('method_count', 0)} methods"
                except Exception:
                    pass

            result = await generate_cadsl_query(
                question=question,
                schema_info=schema_info,
                max_iterations=max_retries,
                similar_tools_context=similar_tools_context,
                reter_client=self.reter_client,
                project_root=None
            )

            if not result.success:
                return {
                    "success": False,
                    "results": [],
                    "count": 0,
                    "cadsl_query": result.query,
                    "query_type": "cadsl",
                    "attempts": result.attempts,
                    "tools_used": result.tools_used,
                    "error": result.error or "Query generation failed"
                }

            generated_query = result.query
            debug_log.debug(f"GENERATED CADSL QUERY:\n{generated_query}")

            execution_state["attempt_delta"] = result.attempts
            execution_state["tools_delta"] = result.tools_used
            exec_result = self._execute_single_cadsl_pipeline(generated_query, execution_state)

            return await self._retry_cadsl_on_empty(
                question, generated_query, exec_result,
                execution_state, max_empty_retries
            )

        except Exception as e:
            debug_log.debug(f"CADSL ERROR: {e}")
            return {
                "success": False,
                "results": [],
                "count": 0,
                "query_type": "cadsl",
                "attempts": execution_state["attempts"],
                "tools_used": execution_state["tools_used"],
                "error": str(e)
            }

    async def _retry_cadsl_on_empty(
        self,
        question: str,
        current_query: str,
        exec_result: Dict[str, Any],
        execution_state: Dict[str, Any],
        max_empty_retries: int
    ) -> Dict[str, Any]:
        """Handle retry logic when CADSL query returns empty or error results."""
        empty_retry_count = 0

        while empty_retry_count < max_empty_retries:
            result_count = exec_result.get("count", 0)
            has_error = not exec_result.get("success", False)
            error_msg = exec_result.get("error")

            if result_count > 0 and not has_error:
                return exec_result

            debug_log.debug(f"CADSL query returned {result_count} results, asking agent to retry...")

            retry_result = await retry_cadsl_query(
                question=question,
                previous_query=current_query,
                result_count=result_count,
                error_message=error_msg if has_error else None,
                reter_client=self.reter_client
            )

            if retry_result.error == "CONFIRM_EMPTY":
                exec_result["agent_confirmed_empty"] = True
                return exec_result

            if retry_result.success and retry_result.query:
                current_query = retry_result.query
                execution_state["attempt_delta"] = retry_result.attempts
                execution_state["tools_delta"] = retry_result.tools_used
                exec_result = self._execute_single_cadsl_pipeline(current_query, execution_state)
                empty_retry_count += 1
            else:
                return exec_result

        return exec_result

    def _fix_bare_reql_block(self, cadsl_query: str) -> str:
        """Auto-fix bare reql blocks by wrapping them in a query definition."""
        import re

        stripped = cadsl_query.strip()

        if stripped.startswith('reql') and not stripped.startswith('reql_'):
            debug_log.debug("AUTO-FIX: Detected bare reql block, wrapping in query definition")

            has_emit = bool(re.search(r'\|\s*emit\s*\{', stripped))

            if has_emit:
                fixed = f'query auto_generated() {{\n    """{stripped[:50]}..."""\n\n    {stripped}\n}}'
            else:
                fixed = f'query auto_generated() {{\n    """{stripped[:50]}..."""\n\n    {stripped}\n    | emit {{ results }}\n}}'

            return fixed

        return cadsl_query

    def _register_nlq_tool(self, app: FastMCP) -> None:
        """Register the natural language query tool."""
        registrar = self

        @app.tool()
        async def natural_language_query(
            question: str,
            max_retries: int = 5,
            timeout: int = 1800,
            max_results: int = 500,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Query code using natural language - translates to CADSL automatically.

            Args:
                question: Natural language question about code
                max_retries: Maximum retry attempts (default: 5)
                timeout: Query timeout in seconds (default: 1800)
                max_results: Maximum results to return (default: 500)

            Returns:
                success, results, count, generated_query, error
            """
            import time
            start_time = time.time()

            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            ensure_nlq_logger_configured()
            debug_log.debug(f"\n{'#'*60}\nNEW NLQ REQUEST\n{'#'*60}")
            debug_log.debug(f"Question: {question}")

            if ctx is None:
                return {"success": False, "error": "Context not available"}

            # Find similar CADSL tools
            from .hybrid_query_engine import find_similar_cadsl_tools
            similar_tools = find_similar_cadsl_tools(question, max_results=5)
            debug_log.debug(f"Similar tools: {[t.name for t in similar_tools]}")

            try:
                async with asyncio.timeout(timeout):
                    result = await registrar._execute_cadsl_query(
                        question, max_retries, similar_tools=similar_tools
                    )

                    if similar_tools:
                        result["similar_tools"] = [t.to_dict() for t in similar_tools]

                    result["execution_time_ms"] = (time.time() - start_time) * 1000
                    return truncate_response(result)

            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Query timed out after {timeout} seconds"
                }

    def _register_cadsl_tool(self, app: FastMCP) -> None:
        """Register the CADSL script execution tool."""
        registrar = self

        @app.tool()
        def execute_cadsl(
            script: str,
            params: Optional[Dict[str, Any]] = None,
            timeout_ms: int = 300000
        ) -> Dict[str, Any]:
            """
            Execute a CADSL script for code analysis.

            Args:
                script: CADSL script string or path to .cadsl file
                params: Optional parameters to pass to the script
                timeout_ms: Timeout in milliseconds (default: 300000)

            Returns:
                success, results, count, tool_name, tool_type, error
            """
            import os
            import time
            from pathlib import Path

            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            start_time = time.time()

            # Determine if script is a file path or inline CADSL
            cadsl_content = script
            source_file = None

            script_stripped = script.strip()
            is_inline_cadsl = (
                script_stripped.startswith('query ') or
                script_stripped.startswith('detector ') or
                script_stripped.startswith('diagram ') or
                script_stripped.startswith('//')
            )

            if not is_inline_cadsl and (script_stripped.endswith('.cadsl') or os.path.sep in script_stripped):
                path = Path(script_stripped)
                if path.exists() and path.is_file():
                    source_file = str(path)
                    with open(path, 'r', encoding='utf-8') as f:
                        cadsl_content = f.read()
                elif not path.exists():
                    return {"success": False, "error": f"CADSL file not found: {script}"}

            try:
                result = registrar.reter_client.execute_cadsl(cadsl_content, params, timeout_ms)
                result["source_file"] = source_file
                result["execution_time_ms"] = (time.time() - start_time) * 1000
                return truncate_response(result)
            except Exception as e:
                return {"success": False, "error": str(e), "source_file": source_file}

    def _register_generate_cadsl_tool(self, app: FastMCP) -> None:
        """Register the generate CADSL tool."""
        registrar = self

        @app.tool()
        async def generate_cadsl(
            question: str,
            max_retries: int = 5,
            timeout: int = 300,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Generate a CADSL query from natural language without executing it.

            Args:
                question: Natural language question about code
                max_retries: Maximum retry attempts (default: 5)
                timeout: Timeout in seconds (default: 300)

            Returns:
                success, cadsl_query, similar_tools, error
            """
            import time
            start_time = time.time()

            if registrar.reter_client is None:
                return {"success": False, "error": "RETER server not connected"}

            ensure_nlq_logger_configured()
            debug_log.debug(f"\n{'#'*60}\nGENERATE CADSL REQUEST\n{'#'*60}")
            debug_log.debug(f"Question: {question}")

            if ctx is None:
                return {"success": False, "error": "Context not available"}

            if not is_agent_sdk_available():
                return {"success": False, "error": "Claude Agent SDK not available"}

            # Get schema info from server
            schema_info = "Schema information unavailable"
            try:
                status = registrar.reter_client.get_status()
                schema_info = f"Codebase has {status.get('class_count', 0)} classes, {status.get('method_count', 0)} methods"
            except Exception:
                pass

            # Find similar CADSL tools
            from .hybrid_query_engine import find_similar_cadsl_tools
            similar_tools = find_similar_cadsl_tools(question, max_results=5)
            similar_tools_context = build_similar_tools_section(similar_tools) if similar_tools else None

            try:
                async with asyncio.timeout(timeout):
                    result = await generate_cadsl_query(
                        question=question,
                        schema_info=schema_info,
                        max_iterations=max_retries,
                        similar_tools_context=similar_tools_context,
                        reter_client=registrar.reter_client,
                        project_root=None
                    )

                    execution_time = (time.time() - start_time) * 1000

                    if result.success and result.query:
                        return {
                            "success": True,
                            "cadsl_query": result.query,
                            "attempts": result.attempts,
                            "tools_used": result.tools_used,
                            "similar_tools": [t.to_dict() for t in similar_tools] if similar_tools else [],
                            "execution_time_ms": execution_time
                        }
                    else:
                        return {
                            "success": False,
                            "cadsl_query": None,
                            "error": result.error or "Failed to generate CADSL query",
                            "execution_time_ms": execution_time
                        }

            except asyncio.TimeoutError:
                return {"success": False, "error": f"Timed out after {timeout} seconds"}
            except Exception as e:
                return {"success": False, "error": str(e)}

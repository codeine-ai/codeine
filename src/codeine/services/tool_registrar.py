"""
Tool Registrar Service

Handles registration and management of MCP tools.
Extracted from LogicalThinkingServer as part of Extract Class refactoring (Fowler Ch. 7).
"""

import asyncio
from typing import Dict, Any, Optional, TYPE_CHECKING
from fastmcp import FastMCP, Context  # Use fastmcp for proper Context injection

from ..logging_config import nlq_debug_logger as debug_log
from ..reter_wrapper import is_initialization_complete
from .initialization_progress import (
    get_initializing_response,
    require_default_instance,
    ComponentNotReadyError,
)

from .reter_operations import ReterOperations
from .state_persistence import StatePersistenceService
from .instance_manager import InstanceManager
from .tools_service import ToolsRegistrar
from .registrars.system_tools import SystemToolsRegistrar
from .nlq_constants import REQL_SYSTEM_PROMPT
from .nlq_helpers import (
    query_instance_schema,
    build_nlq_prompt,
    extract_reql_from_response,
    execute_reql_query,
    is_retryable_error
)
from .response_truncation import truncate_response

if TYPE_CHECKING:
    from .default_instance_manager import DefaultInstanceManager


class ToolRegistrar:
    """
    Manages MCP tool registration.
    Single Responsibility: Register and configure MCP tools.
    """

    def __init__(
        self,
        reter_ops: ReterOperations,
        persistence: StatePersistenceService,
        instance_manager: InstanceManager,
        default_manager: "DefaultInstanceManager"
    ):
        """
        Initialize ToolRegistrar with required services.

        Args:
            reter_ops: Service for RETER operations
            persistence: Service for state persistence
            instance_manager: Service for managing RETER instances
            default_manager: Service for managing default instance
        """
        self.reter_ops = reter_ops
        self.persistence = persistence
        self.instance_manager = instance_manager
        self.default_manager = default_manager

        # Direct tools registration (pass default_manager for RAG)
        self.tools_registrar = ToolsRegistrar(instance_manager, persistence, default_manager)

        # System tools registrar (unified system management)
        self.system_registrar = SystemToolsRegistrar(
            instance_manager, persistence, default_manager, reter_ops
        )

    def register_all_tools(self, app: FastMCP) -> None:
        """
        Register all MCP tools with the application.

        Args:
            app: FastMCP application instance
        """
        self._register_knowledge_tools(app)
        self._register_query_tools(app)
        self.system_registrar.register(app)  # Unified system tool
        self._register_domain_tools(app)
        self._register_experimental_tools(app)

    def _register_knowledge_tools(self, app: FastMCP) -> None:
        """Register knowledge management tools."""

        @app.tool()
        def add_knowledge(
            source: str,
            type: str = "ontology",
            source_id: Optional[str] = None,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Incrementally add knowledge to RETER's semantic memory.

            RETER is an incremental forward-chaining reasoner - knowledge accumulates!
            Each call ADDS facts/rules to the existing knowledge base (doesn't replace).

            Use cases:
            - Add domain ontology (classes, properties, individuals)
            - Add SWRL inference rules (automatically apply to existing facts)
            - Analyze Python code (extract semantic facts from single .py file)
            - Assert new facts (incremental reasoning)

            Args:
                source: Ontology content, file path, or single Python file path
                type: 'ontology' (DL/SWRL), 'python' (.py), 'javascript' (.js/.ts), 'html', 'csharp' (.cs), or 'cpp' (.cpp/.hpp/.h)
                source_id: Optional identifier for selective forgetting later

            Returns:
                success: Whether knowledge was successfully added
                items_added: Number of WMEs (facts/rules) added to RETER
                execution_time_ms: Time taken to add and process knowledge
                source_id: The source ID used (includes timestamp for files)
            """
            try:
                require_default_instance()
            except ComponentNotReadyError as e:
                return e.to_response()
            return self.reter_ops.add_knowledge("default", source, type, source_id, ctx)

        @app.tool()
        def add_external_directory(
            directory: str,
            recursive: bool = True,
            exclude_patterns: list[str] = None,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Load EXTERNAL code files from a directory into a NAMED RETER instance.

            Supports: Python (.py), JavaScript (.js, .mjs, .jsx, .ts, .tsx), HTML (.html, .htm),
                      C# (.cs), C++ (.cpp, .cc, .cxx, .hpp, .h)

            Use this tool to load code from external libraries, dependencies,
            or other codebases that are NOT your main project.

            Args:
                directory: Path to directory containing external code files
                recursive: Whether to recursively search subdirectories (default: True)
                exclude_patterns: List of glob patterns to exclude (e.g., ["test_*.py", "*/tests/*", "node_modules/*"])

            Returns:
                success: Whether operation succeeded
                files_loaded: Number of files successfully loaded (by type: python, javascript, html, csharp, cpp)
                total_files: Total number of files found (by type)
                total_wmes: Total WMEs (facts) added across all files
                errors: List of any errors encountered
                files_with_errors: List of files that failed to load
                execution_time_ms: Total time taken
            """
            try:
                require_default_instance()
            except ComponentNotReadyError as e:
                return e.to_response()
            return self.reter_ops.add_external_directory("default", directory, recursive, exclude_patterns, ctx)

    def _register_query_tools(self, app: FastMCP) -> None:
        """Register query execution tools."""

        @app.tool()
        def quick_query(
            query: str,
            type: str = "reql"
        ) -> Dict[str, Any]:
            """
            Execute a quick query outside of reasoning flow.

            NOTE: For most use cases, prefer using `natural_language_query` instead!
            It translates plain English questions into REQL automatically using LLM.
            Use `quick_query` only when you need precise control over the REQL syntax.

            Automatically checks source validity before executing queries and includes
            warnings if any sources are outdated or deleted.

            Args:
                query: Query string in REQL syntax
                type: 'reql', 'dl', or 'pattern'

            Returns:
                results: Query results
                count: Number of matches
                source_validity: Information about outdated/deleted sources
                warnings: Any warnings about source validity
            """
            try:
                require_default_instance()
            except ComponentNotReadyError as e:
                return e.to_response()
            result = self.reter_ops.quick_query("default", query, type)
            return truncate_response(result)

    def _register_domain_tools(self, app: FastMCP) -> None:
        """Register all RETER domain-specific tools (Python analysis, UML, Gantt, etc.)."""
        self.tools_registrar.register_all_tools(app)

    def _register_experimental_tools(self, app: FastMCP) -> None:
        """Register experimental tools for testing new features."""
        self._register_nlq_tool(app)

    def _register_nlq_tool(self, app: FastMCP) -> None:
        """Register the natural language query tool."""

        @app.tool()
        async def natural_language_query(
            question: str,
            max_retries: int = 5,
            timeout: int = 30,
            max_results: int = 500,
            ctx: Context = None
        ) -> Dict[str, Any]:
            """
            Query CODE STRUCTURE using natural language (translates to REQL).

            **PURPOSE**: Ask questions about code structure, relationships, and patterns.
            This tool translates your natural language question into a REQL query that
            searches the parsed Python codebase (classes, methods, functions, imports, etc.).

            **NOT FOR**: General knowledge questions, documentation content, or semantic
            code search. Use `semantic_search` for finding code by meaning/similarity.

            **See: python://reter/query-patterns for REQL examples if needed**

            Examples:
                - "What classes inherit from BaseTool?"
                - "Find all methods that call the save function"
                - "List modules with more than 5 classes"
                - "Which functions have the most parameters?"
                - "Find functions with magic number 100"
                - "Show string literals containing 'error'"

            Translates natural language questions into REQL queries using LLM,
            executes them against the code knowledge graph, and returns results.

            Args:
                question: Natural language question about code structure (plain English)
                max_retries: Maximum retry attempts on syntax errors (default: 5)
                timeout: Query timeout in seconds (default: 30)
                max_results: Maximum results to return (default: 500)
                ctx: MCP context (injected automatically)

            Returns:
                success: Whether query succeeded
                results: Query results as list of dicts
                count: Number of results
                reql_query: The REQL query that was executed (useful for learning REQL)
                attempts: Number of attempts made
                error: Error message if failed
                truncated: Whether results were truncated (if count > max_results)
            """
            try:
                require_default_instance()
            except ComponentNotReadyError as e:
                return e.to_response()

            debug_log.debug(f"\n{'#'*60}\nNEW NLQ REQUEST\n{'#'*60}")
            debug_log.debug(f"Question: {question}, Instance: default")

            if ctx is None:
                return self._nlq_error_response("Context not available for LLM sampling")

            try:
                reter = self.instance_manager.get_or_create_instance("default")
            except Exception as e:
                return self._nlq_error_response(f"Failed to get RETER instance: {str(e)}")

            schema_info = query_instance_schema(reter)

            # Execute with timeout protection
            try:
                async with asyncio.timeout(timeout):
                    return await self._execute_nlq_with_retries(
                        reter, question, schema_info, max_retries, max_results, ctx
                    )
            except asyncio.TimeoutError:
                debug_log.debug(f"Query timed out after {timeout} seconds")
                return self._nlq_error_response(
                    f"Query timed out after {timeout} seconds. Try a more specific question.",
                    attempts=0
                )

    def _nlq_error_response(self, error: str, query: str = None, attempts: int = 0) -> Dict[str, Any]:
        """Create a standardized error response for NLQ tool."""
        return {
            "success": False,
            "results": [],
            "count": 0,
            "reql_query": query,
            "attempts": attempts,
            "error": error
        }

    async def _execute_nlq_with_retries(
        self,
        reter,
        question: str,
        schema_info: str,
        max_retries: int,
        max_results: int,
        ctx
    ) -> Dict[str, Any]:
        """Execute NLQ with retry logic for syntax errors."""
        attempts = 0
        last_error = None
        generated_query = None

        while attempts < max_retries:
            attempts += 1
            try:
                user_prompt = build_nlq_prompt(
                    question, schema_info, attempts, generated_query, last_error
                )
                debug_log.debug(f"\n{'='*60}\nNLQ ATTEMPT {attempts}/{max_retries}\n{'='*60}")

                response = await ctx.sample(user_prompt, system_prompt=REQL_SYSTEM_PROMPT)
                response_text = response.text if hasattr(response, 'text') else str(response)
                debug_log.debug(f"LLM RAW RESPONSE:\n{response_text}")

                generated_query = extract_reql_from_response(response_text)
                debug_log.debug(f"EXTRACTED REQL QUERY:\n{generated_query}")

                results = execute_reql_query(reter, generated_query)
                total_count = len(results)
                debug_log.debug(f"QUERY SUCCESS: {total_count} results")

                # Check for potential cross-join (excessive results)
                cross_join_threshold = 1000
                if total_count > cross_join_threshold:
                    debug_log.debug(f"CROSS-JOIN DETECTED: {total_count} results exceeds threshold")
                    return {
                        "success": False,
                        "results": [],
                        "count": total_count,
                        "reql_query": generated_query,
                        "attempts": attempts,
                        "error": f"Query returned {total_count} results which suggests a cross-join error. "
                                 f"Please rephrase your question to be more specific.",
                        "warning": "Possible cross-join detected - query may be missing proper join conditions"
                    }

                # Apply result truncation
                truncated = False
                if total_count > max_results:
                    results = results[:max_results]
                    truncated = True
                    debug_log.debug(f"Results truncated from {total_count} to {max_results}")

                response_dict = {
                    "success": True,
                    "results": results,
                    "count": total_count,
                    "reql_query": generated_query,
                    "attempts": attempts,
                    "error": None
                }

                if truncated:
                    response_dict["truncated"] = True
                    response_dict["warning"] = f"Results truncated. Showing {max_results} of {total_count}. Use more specific queries for full results."

                return truncate_response(response_dict)

            except Exception as e:
                last_error = str(e)
                debug_log.debug(f"QUERY ERROR: {last_error}")

                if is_retryable_error(last_error):
                    debug_log.debug(f"Retryable error (attempt {attempts}/{max_retries})")
                    continue
                else:
                    debug_log.debug("Non-retryable error, aborting")
                    return self._nlq_error_response(last_error, generated_query, attempts)

        debug_log.debug(f"MAX RETRIES EXHAUSTED after {attempts} attempts")
        return self._nlq_error_response(
            f"Failed after {max_retries} attempts. Last error: {last_error}",
            generated_query,
            attempts
        )


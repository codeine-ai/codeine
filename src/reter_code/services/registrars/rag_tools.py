"""
RAG Tools Registrar

Registers the semantic_search MCP tool.
All operations go through ReterClient via ZeroMQ (remote-only mode).
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from fastmcp import FastMCP
from .base import ToolRegistrarBase, truncate_mcp_response

if TYPE_CHECKING:
    from ...server.reter_client import ReterClient


class RAGToolsRegistrar(ToolRegistrarBase):
    """
    Registers RAG tools with FastMCP.

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
        default_manager=None,
        tools_filter=None,
        reter_client: Optional["ReterClient"] = None
    ):
        super().__init__(instance_manager, persistence_service, tools_filter, reter_client)

    def register(self, app: FastMCP) -> None:
        """Register RAG tools (respects tools_filter)."""
        if self._should_register("semantic_search"):
            self._register_semantic_search(app)

    def _register_semantic_search(self, app: FastMCP) -> None:
        """Register the semantic_search tool."""
        registrar = self

        @app.tool()
        @truncate_mcp_response
        def semantic_search(
            query: str,
            top_k: int = 10,
            entity_types: Optional[List[str]] = None,
            file_filter: Optional[str] = None,
            include_content: bool = False,
            search_scope: str = "all"
        ) -> Dict[str, Any]:
            """
            Search code and documentation semantically using natural language.

            Uses FAISS vector similarity to find code entities and documentation
            sections that are semantically similar to your query.

            Args:
                query: Natural language search query (e.g., "function that handles authentication")
                top_k: Maximum number of results (default: 10)
                entity_types: Filter by type: ["class", "method", "function", "section", "document", "code_block"]
                file_filter: Glob pattern to filter files (e.g., "src/**/*.py", "docs/**/*.md")
                include_content: Include source code/content in results (default: False)
                search_scope: "all" (code+docs), "code" (Python only), "docs" (Markdown only)

            Returns:
                {
                    "success": True,
                    "results": [
                        {
                            "entity_type": "method",
                            "name": "authenticate_user",
                            "qualified_name": "auth.service.AuthService.authenticate_user",
                            "file": "src/auth/service.py",
                            "line": 45,
                            "end_line": 78,
                            "score": 0.92,
                            "source_type": "python",
                            "docstring": "Authenticate a user with credentials...",
                            "content": "def authenticate_user(...)..."  # if include_content=True
                        },
                        ...
                    ],
                    "count": 10,
                    "query_embedding_time_ms": 12,
                    "search_time_ms": 3,
                    "total_vectors": 1523
                }

            Examples:
                - semantic_search("authentication and JWT tokens")
                - semantic_search("error handling", entity_types=["method", "function"])
                - semantic_search("installation guide", search_scope="docs")
                - semantic_search("database connection", file_filter="src/db/**")
            """
            if registrar.reter_client is None:
                return {
                    "success": False,
                    "error": "RETER server not connected",
                    "results": [],
                    "count": 0,
                }

            try:
                return registrar.reter_client.semantic_search(
                    query=query,
                    top_k=top_k,
                    entity_types=entity_types,
                    file_filter=file_filter,
                    include_content=include_content,
                    search_scope=search_scope
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "results": [],
                    "count": 0,
                }

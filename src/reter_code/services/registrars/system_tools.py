"""
System Tools Registrar

Unified system management tool that consolidates:
- instance_manager (list, list_sources, get_facts, forget, reload, check)
- init_status
- rag_status
- rag_reindex
- reter_info
- initialize_project

All operations go through ReterClient via ZeroMQ (remote-only mode).
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from fastmcp import FastMCP
from .base import ToolRegistrarBase

if TYPE_CHECKING:
    from ...server.reter_client import ReterClient


class SystemToolsRegistrar(ToolRegistrarBase):
    """
    Registers the unified system management tool.

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
        reter_ops=None,
        reter_client: Optional["ReterClient"] = None
    ):
        super().__init__(instance_manager, persistence_service, reter_client=reter_client)

    def register(self, app: FastMCP) -> None:
        """Register the system tool."""
        registrar = self

        @app.tool()
        async def system(
            action: str,
            source: Optional[str] = None,
            force: bool = False
        ) -> Dict[str, Any]:
            """
            Unified system management tool for RETER knowledge base.

            Actions:
            - status: Combined initialization and RAG status
            - info: Version and diagnostic information
            - sources: List all loaded source files
            - facts: Get fact IDs for a source (requires `source`)
            - forget: Remove facts from a source (requires `source`)
            - reload: Reload modified source files (incremental)
            - check: Consistency check of knowledge base
            - initialize: Full re-initialization (reloads everything)
            - reindex: RAG index rebuild (use `force=True` for full rebuild)
            - reset_parser: Force CADSL grammar reload (after grammar.lark changes)

            Args:
                action: One of: status, info, sources, facts, forget, reload, check, initialize, reindex, reset_parser
                source: Source ID or file path (required for facts, forget)
                force: Force full rebuild for reindex action (default: False)

            Returns:
                Action-specific results with success status

            Examples:
                system("status")                    # Comprehensive status
                system("info")                      # Version info
                system("sources")                   # List loaded files
                system("facts", "path/to/file.py")  # Get facts for file
                system("forget", "path/to/file.py") # Forget a file
                system("reload")                    # Reload modified files
                system("check")                     # Consistency check
                system("initialize")                # Full re-init
                system("reindex", force=True)       # Force RAG rebuild
                system("reset_parser")              # Reload CADSL grammar
            """
            if registrar.reter_client is None:
                return {
                    "success": False,
                    "error": "RETER server not connected",
                    "action": action,
                }

            try:
                kwargs = {}
                if source is not None:
                    kwargs["source"] = source
                if force:
                    kwargs["force"] = force
                return registrar.reter_client.system(action, **kwargs)
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "action": action,
                }

"""
Tools Registration

Direct MCP tool registration for all RETER tools.
All operations go through ReterClient via ZeroMQ (remote-only mode).

Refactored to use separate registrar classes for better maintainability.
"""

from typing import Optional, Set, TYPE_CHECKING
from fastmcp import FastMCP

from .registrars import (
    CodeInspectionToolsRegistrar,
    RecommenderToolsRegistrar,
    UnifiedToolsRegistrar,
    RAGToolsRegistrar,
)
from .registrars.base import ToolRegistrarBase

if TYPE_CHECKING:
    from ..server.reter_client import ReterClient


class ToolsRegistrar(ToolRegistrarBase):
    """
    Registers all RETER tools directly with FastMCP.

    All operations go through ReterClient via ZeroMQ.

    ::: This is-in-layer Service-Layer.
    ::: This is a registrar.
    ::: This is-in-process MCP-Server-Process.
    ::: This is stateless.

    Delegates to specialized registrar classes for each tool category.
    """

    def __init__(
        self,
        instance_manager,
        persistence_service,
        default_manager=None,
        tools_filter: Optional[Set[str]] = None,
        reter_client: Optional["ReterClient"] = None
    ):
        """
        Initialize the tools registrar.

        Args:
            instance_manager: Kept for interface compatibility
            persistence_service: Kept for interface compatibility
            default_manager: Kept for interface compatibility
            tools_filter: Optional set of tool names to register. If None, all tools are registered.
            reter_client: ReterClient for remote RETER access via ZeroMQ
        """
        super().__init__(instance_manager, persistence_service, tools_filter, reter_client)

        # Initialize sub-registrars with reter_client
        self._registrars = [
            CodeInspectionToolsRegistrar(instance_manager, persistence_service, tools_filter=tools_filter, reter_client=reter_client),
            RecommenderToolsRegistrar(instance_manager, persistence_service, default_manager, tools_filter=tools_filter, reter_client=reter_client),
            UnifiedToolsRegistrar(instance_manager, persistence_service, tools_filter=tools_filter, reter_client=reter_client),
            RAGToolsRegistrar(instance_manager, persistence_service, default_manager, tools_filter=tools_filter, reter_client=reter_client),
        ]

    def register(self, app: FastMCP) -> None:
        """
        Register all tools with the FastMCP application.

        Args:
            app: FastMCP application instance
        """
        for registrar in self._registrars:
            registrar.register(app)

    def register_all_tools(self, app: FastMCP) -> None:
        """Alias for register() for backwards compatibility."""
        self.register(app)

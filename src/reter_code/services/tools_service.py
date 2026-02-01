"""
Tools Registration

Direct MCP tool registration for all RETER tools.
Refactored to use separate registrar classes for better maintainability.

Consolidation Updates:
- Phase 7: Removed GanttToolsRegistrar, RecommendationsToolsRegistrar,
  RequirementsToolsRegistrar -> replaced by UnifiedToolsRegistrar
- Code Inspection: Removed PythonBasicToolsRegistrar, PythonAdvancedToolsRegistrar,
  UMLToolsRegistrar -> replaced by CodeInspectionToolsRegistrar
- Recommender: Renamed RefactoringToolsRegistrar -> RecommenderToolsRegistrar
- RAG: Added RAGToolsRegistrar for semantic search over code and documentation

Tool Filtering:
- tools_filter parameter allows selective tool registration
- Used by TOOLS_AVAILABLE env var for "default" vs "full" mode
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
    from .default_instance_manager import DefaultInstanceManager


class ToolsRegistrar(ToolRegistrarBase):
    """
    Registers all RETER tools directly with FastMCP.

    ::: This is-in-layer Service-Layer.
    ::: This is a registrar.
    ::: This is-in-process MCP-Server-Process.
    ::: This is stateless.

    Delegates to specialized registrar classes for each tool category.
    Extends ToolRegistrarBase for common functionality (_get_reter,
    _save_snapshot, _ensure_ontology_loaded).
    """

    def __init__(
        self,
        instance_manager,
        persistence_service,
        default_manager: Optional["DefaultInstanceManager"] = None,
        tools_filter: Optional[Set[str]] = None
    ):
        """
        Initialize the tools registrar.

        Args:
            instance_manager: RETER instance manager
            persistence_service: State persistence service
            default_manager: Default instance manager (for RAG integration)
            tools_filter: Optional set of tool names to register. If None, all tools are registered.
        """
        super().__init__(instance_manager, persistence_service)
        self.default_manager = default_manager
        self._tools_filter = tools_filter

        # Initialize sub-registrars with tools_filter
        # Consolidated: CodeInspectionToolsRegistrar replaces Python and UML tools
        # UnifiedToolsRegistrar replaces Session, Gantt, Recommendations, Requirements
        # RecommenderToolsRegistrar provides unified recommender("type", "detector") interface
        # RAGToolsRegistrar provides semantic search over code and documentation
        self._registrars = [
            CodeInspectionToolsRegistrar(instance_manager, persistence_service, tools_filter=tools_filter),
            RecommenderToolsRegistrar(instance_manager, persistence_service, default_manager, tools_filter=tools_filter),
            UnifiedToolsRegistrar(instance_manager, persistence_service, tools_filter=tools_filter),
            RAGToolsRegistrar(instance_manager, persistence_service, default_manager, tools_filter=tools_filter),
        ]

    def register(self, app: FastMCP) -> None:
        """
        Register all tools with the FastMCP application.

        Implements the abstract method from ToolRegistrarBase.

        Args:
            app: FastMCP application instance
        """
        for registrar in self._registrars:
            registrar.register(app)

    def register_all_tools(self, app: FastMCP) -> None:
        """
        Register all tools with the FastMCP application.

        Alias for register() for backwards compatibility.

        Args:
            app: FastMCP application instance
        """
        self.register(app)

"""
Recommender Tools Registrar

Generic recommender tool that dispatches to CADSL detector tools.
All operations go through ReterClient via ZeroMQ (remote-only mode).

Usage:
- recommender() - lists all recommender categories
- recommender("smells") - queues tasks for all smell detectors
- recommender("smells", "large_classes") - runs specific detector
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING
from fastmcp import FastMCP
from .base import ToolRegistrarBase, truncate_mcp_response

if TYPE_CHECKING:
    from ...server.reter_client import ReterClient


class RecommenderToolsRegistrar(ToolRegistrarBase):
    """
    Registers the unified recommender tool with FastMCP.

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
        """Register the recommender tool (respects tools_filter)."""
        if not self._should_register("recommender"):
            return

        registrar = self

        @app.tool()
        @truncate_mcp_response
        def recommender(
            recommender_type: Optional[str] = None,
            detector_name: Optional[str] = None,
            session_instance: str = "default",
            categories: Optional[List[str]] = None,
            severities: Optional[List[str]] = None,
            detector_type: str = "all",
            params: Optional[Dict[str, Any]] = None,
            create_tasks: bool = False,
            link_to_thought: Optional[str] = None
        ) -> Dict[str, Any]:
            """
            Unified recommender tool for code analysis and recommendations.

            **See: recipe://refactoring/index for refactoring recipes**

            **recommender()**: Queues tasks for each recommender type
            **recommender("refactoring")**: Queues tasks for all detectors
            **recommender("refactoring", "god_class")**: Runs specific detector

            Args:
                recommender_type: Type of recommender. If None, queues tasks for all types.
                detector_name: Specific detector to run. If None, queues all detectors as tasks.
                session_instance: Session instance for storing tasks
                categories: Filter detectors by category
                severities: Filter by severity: low, medium, high
                detector_type: "all", "improving", or "patterns" (refactoring only)
                params: Override detector defaults
                create_tasks: Auto-create tasks from high-priority findings
                link_to_thought: Link recommendations to a thought ID

            Returns:
                Without recommender_type: Tasks created for each recommender type
                Without detector_name: Tasks created for each detector
                With detector_name: Detection results and recommendations
            """
            if registrar.reter_client is None:
                return {
                    "success": False,
                    "error": "RETER server not connected",
                }

            try:
                return registrar.reter_client.recommender(
                    recommender_type=recommender_type,
                    detector_name=detector_name,
                    session_instance=session_instance,
                    categories=categories,
                    severities=severities,
                    detector_type=detector_type,
                    params=params,
                    create_tasks=create_tasks,
                    link_to_thought=link_to_thought
                )
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                }

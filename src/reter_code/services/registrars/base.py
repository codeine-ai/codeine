"""
Base Tool Registrar

Common functionality for all tool registrars.
All operations go through ReterClient via ZeroMQ (remote-only mode).
"""

from typing import Dict, Any, Optional, Callable, TypeVar, Set, TYPE_CHECKING
from pathlib import Path
from functools import wraps

from ..response_truncation import truncate_response

if TYPE_CHECKING:
    from ...server.reter_client import ReterClient

T = TypeVar('T')


def truncate_mcp_response(func: Callable[..., Dict[str, Any]]) -> Callable[..., Dict[str, Any]]:
    """
    Decorator to truncate MCP tool responses to fit within size limits.

    Applies truncate_response() to the result of any MCP tool function.
    The size limit is controlled by RETER_MCP_MAX_RESPONSE_SIZE env var.

    Example:
        @app.tool()
        @truncate_mcp_response
        def my_tool(...) -> Dict[str, Any]:
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Dict[str, Any]:
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            return truncate_response(result)
        return result
    return wrapper


def truncate_mcp_response_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Async version of truncate_mcp_response decorator.

    Example:
        @app.tool()
        @truncate_mcp_response_async
        async def my_tool(...) -> Dict[str, Any]:
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Dict[str, Any]:
        result = await func(*args, **kwargs)
        if isinstance(result, dict):
            return truncate_response(result)
        return result
    return wrapper


class ToolRegistrarBase:
    """
    Base class with common functionality for tool registrars.

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
        tools_filter: Optional[Set[str]] = None,
        reter_client: Optional["ReterClient"] = None
    ):
        """
        Initialize the base tool registrar.

        Args:
            instance_manager: RETER instance manager (kept for interface compatibility)
            persistence_service: State persistence service (kept for interface compatibility)
            tools_filter: Optional set of tool names to register. If None, all tools are registered.
            reter_client: ReterClient for remote RETER access via ZeroMQ
        """
        self.instance_manager = instance_manager
        self.persistence = persistence_service
        self._tools_filter = tools_filter
        self.reter_client = reter_client

    def _should_register(self, tool_name: str) -> bool:
        """
        Check if a tool should be registered based on the tools_filter.

        Args:
            tool_name: Name of the tool to check

        Returns:
            True if the tool should be registered, False otherwise
        """
        if self._tools_filter is None:
            return True  # No filter = register all tools
        return tool_name in self._tools_filter

    def register(self, app) -> None:
        """Register tools with FastMCP. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement register()")

"""
RETER Console UI.

Rich terminal interface for RETER server with live updates.

::: This is-in-layer UI-Layer.
::: This is-in-component Console-UI.
::: This depends-on rich.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from rich.console import Console
    from rich.layout import Layout
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.table import Table
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

if TYPE_CHECKING:
    from .reter_server import ReterServer


@dataclass
class QueryLogEntry:
    """Single query log entry."""
    timestamp: float
    method: str
    duration_ms: float
    result_count: int
    error: Optional[str] = None

    @property
    def time_str(self) -> str:
        """Format timestamp as HH:MM:SS."""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")


@dataclass
class ServerStatus:
    """Server status information."""
    started_at: float = field(default_factory=time.time)
    total_sources: int = 0
    total_wmes: int = 0
    total_vectors: int = 0
    connected_clients: int = 0
    queries_count: int = 0
    errors_count: int = 0
    avg_query_time_ms: float = 0.0

    # Progress tracking
    current_operation: Optional[str] = "Initializing..."  # Start with initializing
    progress_current: int = 0
    progress_total: int = 0
    current_file: Optional[str] = None  # Current file being processed
    initialized: bool = False  # True when server is ready


class ConsoleUI:
    """Rich console output for RETER server.

    ::: This is-defined-in Console-UI.
    ::: This displays-status ServerStatus.
    ::: This logs-queries QueryLogEntry.

    Provides a live-updating terminal interface showing:
    - Server status and statistics
    - Recent query log
    - Progress bars for long operations
    - Client connections
    """

    MAX_LOG_ENTRIES = 50

    def __init__(self, server: "ReterServer"):
        """Initialize console UI.

        Args:
            server: Reference to RETER server for stats
        """
        if not RICH_AVAILABLE:
            raise ImportError("Rich library not available. Install with: pip install rich")

        self.server = server
        self.console = Console()
        self.live: Optional[Live] = None

        self.status = ServerStatus()
        self.query_log: deque[QueryLogEntry] = deque(maxlen=self.MAX_LOG_ENTRIES)

        self._running = False
        self._last_size = (0, 0)  # Track terminal size for resize detection

    def __rich__(self) -> Layout:
        """Return layout for Rich rendering - called on every refresh."""
        return self._build_layout()

    def start(self) -> None:
        """Start live display."""
        self._running = True
        self.live = Live(
            self,  # Pass self - Rich will call __rich__() on each refresh
            console=self.console,
            refresh_per_second=4,
            screen=False
        )
        self.live.start()

    def stop(self) -> None:
        """Stop live display."""
        self._running = False
        if self.live:
            self.live.stop()
            self.live = None

    def _build_layout(self) -> Layout:
        """Build console layout with panels."""
        layout = Layout()

        # Get terminal size for dynamic layout
        term_height = self.console.size.height

        # Calculate sizes based on terminal height
        # Minimum heights: header=3, footer=3, progress=6, main gets the rest
        header_size = 3
        footer_size = 3
        progress_size = min(8, max(6, term_height // 6))  # 6-8 lines for progress

        layout.split_column(
            Layout(name="header", size=header_size),
            Layout(name="main"),
            Layout(name="progress", size=progress_size),
            Layout(name="footer", size=footer_size)
        )

        layout["main"].split_row(
            Layout(name="status", ratio=1),
            Layout(name="queries", ratio=2)
        )

        # Update panels
        layout["header"].update(self._build_header())
        layout["status"].update(self._build_status_panel())
        layout["queries"].update(self._build_query_panel())
        layout["progress"].update(self._build_progress_panel())
        layout["footer"].update(self._build_footer())

        return layout

    def _build_header(self) -> Panel:
        """Build header panel."""
        title = Text()
        title.append("RETER Server", style="bold blue")
        title.append(" v0.1.0", style="dim")

        # Show port (only if bound)
        port = self.server._actual_query_port
        if port > 0:
            title.append(f"  [tcp://127.0.0.1:{port}]", style="green")
        else:
            title.append("  [binding...]", style="yellow")

        # Show project root
        if self.server.config.project_root:
            root_str = str(self.server.config.project_root)
            # Truncate if too long
            max_len = 50
            if len(root_str) > max_len:
                root_str = "..." + root_str[-(max_len-3):]
            title.append(f"  [{root_str}]", style="cyan")

        return Panel(title, style="blue")

    def _build_status_panel(self) -> Panel:
        """Build status panel."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Label", style="dim")
        table.add_column("Value", style="bold")

        # Uptime
        uptime = time.time() - self.status.started_at
        uptime_str = self._format_duration(uptime)
        table.add_row("Uptime", uptime_str)

        # Stats from server
        stats = self.server.stats
        table.add_row("", "")
        table.add_row("Sources", str(self.status.total_sources))
        table.add_row("Facts", f"{self.status.total_wmes:,}")
        table.add_row("Vectors", f"{self.status.total_vectors:,}")
        table.add_row("", "")
        table.add_row("Queries", str(stats.get("requests_handled", 0)))
        table.add_row("Errors", str(stats.get("errors", 0)))
        table.add_row("Avg Time", f"{stats.get('avg_request_time_ms', 0):.1f}ms")

        return Panel(table, title="Status", border_style="blue")

    def _build_progress_panel(self) -> Panel:
        """Build progress panel for current operation."""
        content = Text()

        if self.status.current_operation:
            # Operation name
            content.append(self.status.current_operation, style="bold yellow")

            # Progress bar (only show if we have progress data)
            if self.status.progress_total > 0:
                percent = self.status.progress_current / self.status.progress_total * 100

                bar_width = 50
                filled = int(bar_width * percent / 100)
                content.append("\n  [", style="dim")  # Single newline
                content.append("█" * filled, style="green")
                content.append("░" * (bar_width - filled), style="dim")
                content.append("]", style="dim")
                content.append(f"  {percent:5.1f}%", style="bold white")
                content.append(f"   {self.status.progress_current:,} / {self.status.progress_total:,}", style="dim")

            # Current file - always show on new line
            content.append("\n  ")  # Single newline
            if self.status.current_file:
                content.append("→ ", style="cyan")
                # Show more of the path since we have space
                display_path = self._format_file_path(self.status.current_file, max_width=80)
                content.append(display_path, style="cyan")
            else:
                content.append("→ ", style="dim")
                content.append("waiting...", style="dim")
        elif self.status.initialized:
            content.append("Ready", style="bold green")
            content.append(" - Server is idle, waiting for queries", style="dim")
        else:
            content.append("Starting up...", style="bold yellow")

        return Panel(content, title="Progress", border_style="yellow")

    def _build_query_panel(self) -> Panel:
        """Build query log panel."""
        table = Table(show_header=True, box=None, padding=(0, 1))
        table.add_column("Time", style="dim", width=8)
        table.add_column("Method", width=15)
        table.add_column("Results", justify="right", width=8)
        table.add_column("Time", justify="right", width=8)

        # Show recent queries (most recent first)
        for entry in reversed(list(self.query_log)[-20:]):
            time_str = entry.time_str
            method = entry.method

            if entry.error:
                result_str = Text("ERROR", style="red")
            else:
                result_str = str(entry.result_count)

            duration_str = f"{entry.duration_ms:.0f}ms"

            # Color code by duration
            if entry.duration_ms > 1000:
                duration_style = "red"
            elif entry.duration_ms > 100:
                duration_style = "yellow"
            else:
                duration_style = "green"

            table.add_row(
                time_str,
                method,
                result_str,
                Text(duration_str, style=duration_style)
            )

        return Panel(table, title="Query Log", border_style="blue")

    def _build_footer(self) -> Panel:
        """Build footer panel."""
        text = Text()
        text.append("[Q]", style="bold")
        text.append("uery stats  ", style="dim")
        text.append("[C]", style="bold")
        text.append("lients  ", style="dim")
        text.append("[L]", style="bold")
        text.append("ogs  ", style="dim")
        text.append("[Ctrl+C]", style="bold")
        text.append(" Exit", style="dim")

        return Panel(text, style="dim")

    def _format_duration(self, seconds: float) -> str:
        """Format duration as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.0f}m"
        else:
            hours = seconds / 3600
            mins = (seconds % 3600) / 60
            return f"{hours:.0f}h {mins:.0f}m"

    def _format_file_path(self, path: str, max_width: int = 35) -> str:
        """Format file path for display, keeping most informative parts.

        Strategy:
        - Always show the filename
        - Show as much of the parent path as fits
        - Use ... to indicate truncation in the middle
        """
        import os.path

        # Normalize separators
        path = path.replace("\\", "/")

        # If it fits, show it all
        if len(path) <= max_width:
            return path

        # Split into parts
        parts = path.split("/")
        filename = parts[-1]

        # If just filename is too long, truncate it
        if len(filename) > max_width:
            return filename[:max_width - 3] + "..."

        # Try to fit parent folder + filename
        if len(parts) >= 2:
            parent = parts[-2]
            short_path = f"{parent}/{filename}"
            if len(short_path) <= max_width:
                return short_path

            # Try with ellipsis prefix
            short_path = f".../{parent}/{filename}"
            if len(short_path) <= max_width:
                return short_path

        # Fall back to just filename with ellipsis
        result = f".../{filename}"
        if len(result) <= max_width:
            return result

        # Last resort: truncate filename
        available = max_width - 4  # for ".../""
        return f".../{filename[:available]}"

    def log_query(
        self,
        method: str,
        duration_ms: float,
        result_count: int,
        error: Optional[str] = None
    ) -> None:
        """Log a query execution.

        Args:
            method: Method name
            duration_ms: Execution time
            result_count: Number of results
            error: Error message if failed
        """
        entry = QueryLogEntry(
            timestamp=time.time(),
            method=method,
            duration_ms=duration_ms,
            result_count=result_count,
            error=error
        )
        self.query_log.append(entry)
        self._refresh()

    def update_status(
        self,
        total_sources: Optional[int] = None,
        total_wmes: Optional[int] = None,
        total_vectors: Optional[int] = None,
        connected_clients: Optional[int] = None
    ) -> None:
        """Update server status.

        Args:
            total_sources: Number of loaded sources
            total_wmes: Number of facts
            total_vectors: Number of RAG vectors
            connected_clients: Number of connected clients
        """
        if total_sources is not None:
            self.status.total_sources = total_sources
        if total_wmes is not None:
            self.status.total_wmes = total_wmes
        if total_vectors is not None:
            self.status.total_vectors = total_vectors
        if connected_clients is not None:
            self.status.connected_clients = connected_clients
        self._refresh()

    def update_progress(
        self,
        operation: Optional[str],
        current: int = 0,
        total: int = 0
    ) -> None:
        """Update progress display.

        Args:
            operation: Current operation name (None to clear)
            current: Current progress value
            total: Total progress value
        """
        self.status.current_operation = operation
        self.status.progress_current = current
        self.status.progress_total = total
        self._refresh()

    # =========================================================================
    # ConsoleProgress-compatible methods for initialization callbacks
    # =========================================================================

    def set_phase(self, phase: str) -> None:
        """Set current phase description."""
        self.status.current_operation = phase
        self._refresh()

    def start_gitignore_loading(self) -> None:
        """Start gitignore loading phase."""
        self.status.current_operation = "Loading .gitignore patterns..."
        self.status.progress_current = 0
        self.status.progress_total = 0
        self._refresh()

    def update_gitignore_progress(self, path: str) -> None:
        """Update gitignore progress with current directory."""
        self.status.current_file = path
        self.status.progress_current += 1
        self._refresh()

    def end_gitignore_loading(self, pattern_count: int) -> None:
        """End gitignore loading."""
        self.status.current_file = None
        self.status.progress_total = pattern_count
        self.status.progress_current = pattern_count
        self._refresh()

    def start_scan(self, message: str = "Scanning files") -> None:
        """Start file scanning phase."""
        self.status.current_operation = message
        self.status.current_file = None
        self.status.progress_current = 0
        self.status.progress_total = 0
        self._refresh()

    def end_scan(self, file_count: int) -> None:
        """End scanning phase."""
        self.status.total_sources = file_count
        self.status.progress_total = file_count
        self.status.progress_current = file_count
        self._refresh()

    def start_file_loading(self, total: int) -> None:
        """Start file loading phase."""
        self.status.current_operation = "Loading files..."
        self.status.progress_total = total
        self.status.progress_current = 0
        self.status.current_file = "Starting..."  # Placeholder until first file
        self._refresh()

    def update_file_progress(self, current: int, total: int, filename: str) -> None:
        """Update file loading progress."""
        self.status.progress_current = current
        self.status.progress_total = total
        self.status.total_sources = current
        self.status.current_file = filename
        self._refresh()

    def end_file_loading(self) -> None:
        """End file loading phase."""
        self.status.current_operation = None
        self.status.current_file = None
        self._refresh()

    def start_entity_processing(self, total: int) -> None:
        """Start entity processing phase."""
        self.status.current_operation = "Processing entities..."
        self.status.progress_total = total
        self.status.progress_current = 0
        self._refresh()

    def update_entity_progress(self, current: int, total: int) -> None:
        """Update entity processing progress."""
        self.status.progress_current = current
        self.status.progress_total = total
        self.status.total_wmes = current
        self._refresh()

    def end_entity_processing(self) -> None:
        """End entity processing phase."""
        self.status.current_operation = None
        self.status.current_file = None
        self._refresh()

    def start_embedding_loading(self, model_name: str) -> None:
        """Start embedding model loading."""
        self.status.current_operation = f"Loading {model_name}..."
        self.status.current_file = None
        self.status.progress_current = 0
        self.status.progress_total = 0
        self._refresh()

    def end_embedding_loading(self) -> None:
        """End embedding model loading."""
        # Don't clear operation - next phase will set it
        self._refresh()

    def start_rag_indexing(self, total: int = 0) -> None:
        """Start RAG indexing phase."""
        self.status.current_operation = "Creating embeddings..."
        self.status.progress_total = total
        self.status.progress_current = 0
        self._refresh()

    def update_rag_progress(self, current: int, total: int) -> None:
        """Update RAG indexing progress."""
        self.status.progress_current = current
        self.status.progress_total = total
        self.status.total_vectors = current
        self._refresh()

    def end_rag_indexing(self, vectors_indexed: int) -> None:
        """End RAG indexing phase."""
        self.status.total_vectors = vectors_indexed
        self.status.current_operation = None
        self._refresh()

    def set_component_ready(self, name: str) -> None:
        """Mark component as ready."""
        pass  # Could add component status tracking

    def set_component_error(self, name: str) -> None:
        """Mark component as errored."""
        pass

    def mark_initialized(self) -> None:
        """Mark server as fully initialized and ready."""
        self.status.initialized = True
        self.status.current_operation = None
        self.status.current_file = None
        self.status.progress_current = 0
        self.status.progress_total = 0
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the display."""
        if self.live and self._running:
            self.live.update(self._build_layout())


class NoOpConsoleUI:
    """No-op console UI when Rich is not available."""

    def __init__(self, server: Any):
        pass

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def log_query(self, *args, **kwargs) -> None:
        pass

    def update_status(self, *args, **kwargs) -> None:
        pass

    def update_progress(self, *args, **kwargs) -> None:
        pass

    # ConsoleProgress-compatible no-ops
    def set_phase(self, phase: str) -> None:
        pass

    def start_gitignore_loading(self) -> None:
        pass

    def update_gitignore_progress(self, path: str) -> None:
        pass

    def end_gitignore_loading(self, pattern_count: int) -> None:
        pass

    def start_scan(self, message: str = "Scanning files") -> None:
        pass

    def end_scan(self, file_count: int) -> None:
        pass

    def start_file_loading(self, total: int) -> None:
        pass

    def update_file_progress(self, current: int, total: int, filename: str) -> None:
        pass

    def end_file_loading(self) -> None:
        pass

    def start_entity_processing(self, total: int) -> None:
        pass

    def update_entity_progress(self, current: int, total: int) -> None:
        pass

    def end_entity_processing(self) -> None:
        pass

    def start_embedding_loading(self, model_name: str) -> None:
        pass

    def end_embedding_loading(self) -> None:
        pass

    def start_rag_indexing(self, total: int = 0) -> None:
        pass

    def update_rag_progress(self, current: int, total: int) -> None:
        pass

    def end_rag_indexing(self, vectors_indexed: int) -> None:
        pass

    def set_component_ready(self, name: str) -> None:
        pass

    def set_component_error(self, name: str) -> None:
        pass

    def mark_initialized(self) -> None:
        pass


# Export appropriate class based on Rich availability
if RICH_AVAILABLE:
    __all__ = ["ConsoleUI", "QueryLogEntry", "ServerStatus"]
else:
    ConsoleUI = NoOpConsoleUI  # type: ignore
    __all__ = ["ConsoleUI"]

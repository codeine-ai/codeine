"""
Logging Configuration for RETER MCP Server.

Provides centralized logger setup for debug trace and NLQ debug logs.
All loggers write to files in the auto-detected snapshots directory.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Snapshot directory priority (same as state_persistence.py):
# 1. RETER_SNAPSHOTS_DIR (explicit)
# 2. RETER_PROJECT_ROOT/.reter_code (if set)
# 3. None (don't create file handlers until project root is known)
# This ensures logs go to the same directory as .default.reter
def _get_log_directory() -> Optional[Path]:
    """Get the log directory path (same as snapshots_dir in state_persistence).

    Returns None if RETER_PROJECT_ROOT is not set, to avoid creating logs
    in the wrong directory during early module imports.
    """
    log_dir = os.getenv("RETER_SNAPSHOTS_DIR")
    if not log_dir:
        project_root = os.getenv("RETER_PROJECT_ROOT")
        if project_root:
            log_dir = str(Path(project_root) / ".reter_code")
        else:
            # Don't fall back to CWD - wait for RETER_PROJECT_ROOT to be set
            return None
    return Path(log_dir)


def _ensure_log_directory() -> Optional[Path]:
    """Ensure log directory exists and return its path.

    Returns None if log directory is not configured yet.
    """
    log_dir = _get_log_directory()
    if log_dir is None:
        return None
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


# Check if debug logging is enabled via environment variable
# Set RETER_DEBUG_LOG="" to disable
_debug_log_env = os.getenv("RETER_DEBUG_LOG")
DEBUG_LOG_ENABLED = _debug_log_env is None or _debug_log_env != ""


def _create_file_handler(log_filename: str) -> Optional[logging.FileHandler]:
    """
    Create a file handler for the specified log file.

    Args:
        log_filename: Name of the log file (e.g., 'debug_trace.log')

    Returns:
        Configured FileHandler, or None if logging is disabled or directory not configured
    """
    if not DEBUG_LOG_ENABLED:
        return None

    try:
        log_dir = _ensure_log_directory()
        if log_dir is None:
            # RETER_PROJECT_ROOT not set yet, skip file handler
            return None
        log_path = log_dir / log_filename
        handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        return handler
    except Exception:
        return None


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every emit.

    ::: This is-in-layer Infrastructure-Layer.
    ::: This is a handler.
    ::: This is-in-process Main-Process.
    ::: This is stateless.
    """
    def emit(self, record):
        super().emit(record)
        self.flush()


def _create_stderr_handler() -> logging.StreamHandler:
    """Create a stderr handler for console output with auto-flush."""
    handler = FlushingStreamHandler(sys.stderr)
    # If stderr is suppressed, set level to effectively disable
    if _stderr_suppressed:
        handler.setLevel(logging.CRITICAL + 1)
    else:
        handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    return handler


_stderr_suppressed = False


def get_debug_trace_logger() -> logging.Logger:
    """
    Get the debug trace logger for RETER wrapper operations.

    This logger is used for tracing C++ calls and debugging hangs.
    Output goes to .reter_code/debug_trace.log and stderr

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("reter.debug_trace")

    # Only configure once
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Don't propagate to root logger

        # File handler
        file_handler = _create_file_handler("debug_trace.log")
        if file_handler:
            logger.addHandler(file_handler)

        # Stderr handler
        stderr_handler = _create_stderr_handler()
        logger.addHandler(stderr_handler)

    return logger


def get_nlq_debug_logger() -> logging.Logger:
    """
    Get the NLQ debug logger for natural language query operations.

    This logger is used for tracing NLQ query generation and execution.
    Output goes to .reter_code/nlq_debug.log and stderr.

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("reter.nlq_debug")

    # Only configure once
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Don't propagate to root logger

        # File handler
        file_handler = _create_file_handler("nlq_debug.log")
        if file_handler:
            logger.addHandler(file_handler)

        # Stderr handler for real-time visibility
        stderr_handler = _create_stderr_handler()
        logger.addHandler(stderr_handler)

    return logger


# Track configured log directory for reconfiguration
_configured_log_dir: Optional[Path] = None

# Track loggers configured via configure_logger_for_debug_trace()
# so we can update them when reconfigure_log_directory() is called
_configured_loggers: list = []


def ensure_nlq_logger_configured() -> logging.Logger:
    """
    Ensure NLQ logger is configured with the correct directory.

    Call this before logging to ensure the logger points to the right directory,
    especially after RETER_PROJECT_ROOT is set.

    Returns:
        Configured logger instance
    """
    global _configured_log_dir

    current_dir = _get_log_directory()
    logger = logging.getLogger("reter.nlq_debug")

    # Reconfigure if directory changed or no handlers
    if _configured_log_dir != current_dir or not logger.handlers:
        # Remove old handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # File handler
        file_handler = _create_file_handler("nlq_debug.log")
        if file_handler:
            logger.addHandler(file_handler)

        # Stderr handler for real-time visibility
        stderr_handler = _create_stderr_handler()
        logger.addHandler(stderr_handler)

        _configured_log_dir = current_dir

    return logger


# Pre-create loggers for import convenience
debug_trace_logger = get_debug_trace_logger()
nlq_debug_logger = get_nlq_debug_logger()


def reconfigure_log_directory() -> None:
    """
    Reconfigure all loggers to use the correct directory.

    Call this after setting RETER_PROJECT_ROOT to ensure logs go to the right place.
    """
    global _configured_log_dir, debug_trace_logger, nlq_debug_logger

    current_dir = _get_log_directory()

    # Skip if directory not configured yet (RETER_PROJECT_ROOT not set)
    if current_dir is None:
        return

    # Skip if directory hasn't changed
    if _configured_log_dir == current_dir:
        return

    _configured_log_dir = current_dir

    # Reconfigure debug_trace_logger
    for handler in debug_trace_logger.handlers[:]:
        handler.close()
        debug_trace_logger.removeHandler(handler)

    file_handler = _create_file_handler("debug_trace.log")
    if file_handler:
        debug_trace_logger.addHandler(file_handler)
    stderr_handler = _create_stderr_handler()
    debug_trace_logger.addHandler(stderr_handler)

    # Reconfigure nlq_debug_logger
    for handler in nlq_debug_logger.handlers[:]:
        handler.close()
        nlq_debug_logger.removeHandler(handler)

    file_handler = _create_file_handler("nlq_debug.log")
    if file_handler:
        nlq_debug_logger.addHandler(file_handler)
    stderr_handler = _create_stderr_handler()
    nlq_debug_logger.addHandler(stderr_handler)

    # Also update all loggers that were configured via configure_logger_for_debug_trace()
    # They need the new file handler too
    debug_file_handler = None
    for handler in debug_trace_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            debug_file_handler = handler
            break

    if debug_file_handler:
        for logger in _configured_loggers:
            # Check if this logger already has a file handler
            has_file_handler = any(isinstance(h, logging.FileHandler) for h in logger.handlers)
            if not has_file_handler:
                logger.addHandler(debug_file_handler)


def configure_logger_for_debug_trace(logger_name: str) -> logging.Logger:
    """
    Configure a logger to also write to debug_trace.log.

    Args:
        logger_name: Name of the logger to configure (e.g., __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)  # Enable all log levels
    for handler in debug_trace_logger.handlers:
        if handler not in logger.handlers:
            logger.addHandler(handler)
    # Track this logger so we can update it when reconfigure_log_directory() is called
    if logger not in _configured_loggers:
        _configured_loggers.append(logger)
    return logger


def suppress_stderr_logging():
    """
    Suppress stderr logging for all debug loggers.

    Call this when using Rich progress UI to avoid log spam in the console.
    File logging continues to work normally.
    """
    global _stderr_suppressed
    _stderr_suppressed = True

    # Suppress on known loggers
    for logger in [debug_trace_logger, nlq_debug_logger]:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.CRITICAL + 1)  # Effectively disable

    # Also suppress on ALL loggers that might have stderr handlers
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.CRITICAL + 1)


def restore_stderr_logging():
    """
    Restore stderr logging for all debug loggers.

    Call this after Rich progress UI is done.
    """
    global _stderr_suppressed
    _stderr_suppressed = False
    for logger in [debug_trace_logger, nlq_debug_logger]:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(logging.DEBUG)


def is_stderr_suppressed() -> bool:
    """
    Check if stderr output is currently suppressed.

    Use this to guard print() statements that output to stderr when Rich
    console is active. This avoids interfering with the Rich UI.

    Returns:
        True if stderr should be suppressed (Rich console is active)
    """
    return _stderr_suppressed

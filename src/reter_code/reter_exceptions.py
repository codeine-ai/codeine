"""
RETER Exception Hierarchy

Contains all exception classes used by the RETER integration layer.
"""


class ReterError(Exception):
    """
    Base exception for all RETER operations.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterFileError(ReterError):
    """
    Exception for file-related RETER operations (save/load).

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterFileNotFoundError(ReterFileError):
    """
    Raised when a RETER snapshot file is not found.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterSaveError(ReterFileError):
    """
    Raised when saving RETER network fails.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterLoadError(ReterFileError):
    """
    Raised when loading RETER network fails.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterQueryError(ReterError):
    """
    Exception for query-related RETER operations.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class ReterOntologyError(ReterError):
    """
    Exception for ontology/knowledge loading errors.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.
    """
    pass


class DefaultInstanceNotInitialised(ReterError):
    """
    Raised when attempting to access RETER before initialization is complete.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a exception.

    This exception is thrown by ReterWrapper and RAGIndexManager when:
    - Server is starting up and background initialization hasn't completed
    - Embedding model is still loading
    - Default instance Python files are still being indexed

    MCP tools should catch this exception and return an appropriate error
    message to the client indicating they should wait and retry.
    """
    pass


__all__ = [
    "ReterError",
    "ReterFileError",
    "ReterFileNotFoundError",
    "ReterSaveError",
    "ReterLoadError",
    "ReterQueryError",
    "ReterOntologyError",
    "DefaultInstanceNotInitialised",
]

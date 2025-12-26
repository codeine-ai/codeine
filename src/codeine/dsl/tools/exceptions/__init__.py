"""
Exception Handling Detectors - Identify exception handling issues.

All tools in this package use @detector decorator and produce findings.
"""

from .silent_exception import silent_exception_swallowing
from .general_exception import too_general_exceptions
from .generic_raise import generic_exception_raising
from .error_codes import error_codes_over_exceptions
from .finally_cleanup import finally_without_context_manager

__all__ = [
    "silent_exception_swallowing",
    "too_general_exceptions",
    "generic_exception_raising",
    "error_codes_over_exceptions",
    "finally_without_context_manager",
]

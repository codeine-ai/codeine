"""
Pattern Detectors - Identify design patterns and code patterns.

All tools in this package use @detector decorator and produce findings.
"""

from .decorator_usage import find_decorator_usage
from .magic_methods import find_magic_methods
from .interface_impl import find_interface_implementations
from .public_api import find_public_api
from .singleton import find_singleton_pattern
from .factory import find_factory_pattern

__all__ = [
    "find_decorator_usage",
    "find_magic_methods",
    "find_interface_implementations",
    "find_public_api",
    "find_singleton_pattern",
    "find_factory_pattern",
]

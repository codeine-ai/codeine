"""
Test Coverage Detectors - Identify testing gaps and coverage issues.

All tools in this package use @detector decorator and produce findings.
"""

from .untested_classes import untested_classes
from .untested_functions import untested_functions
from .untested_methods import untested_methods
from .partial_coverage import partial_class_coverage
from .complex_untested import complex_untested
from .high_fanout_untested import high_fanout_untested
from .public_api_untested import public_api_untested
from .shallow_tests import shallow_tests
from .large_untested_modules import large_untested_modules
from .test_fixtures import find_test_fixtures

__all__ = [
    "untested_classes",
    "untested_functions",
    "untested_methods",
    "partial_class_coverage",
    "complex_untested",
    "high_fanout_untested",
    "public_api_untested",
    "shallow_tests",
    "large_untested_modules",
    "find_test_fixtures",
]

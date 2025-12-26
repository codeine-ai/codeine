"""
Inheritance Refactoring Detectors - Identify inheritance-related refactoring opportunities.

All tools in this package use @detector decorator and produce findings.

Note: pull_up_method and push_down_method are in refactoring/ package.
"""

from .remove_subclass import remove_subclass_candidates
from .extract_superclass import extract_superclass_candidates
from .collapse_hierarchy import collapse_hierarchy_candidates
from .replace_with_delegate import replace_with_delegate_candidates

__all__ = [
    "remove_subclass_candidates",
    "extract_superclass_candidates",
    "collapse_hierarchy_candidates",
    "replace_with_delegate_candidates",
]

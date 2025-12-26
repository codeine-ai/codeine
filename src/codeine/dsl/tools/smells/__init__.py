"""
Smell Detectors - Code smell detection tools.

Detects common code quality issues:
- god_class: Classes doing too much (also exported as large_classes for compatibility)
- long_methods: Methods with too many lines
- long_parameter_list: Methods with too many parameters
- data_class: Classes with only getters/setters
- feature_envy: Methods using other class's data excessively
- dead_code: Unused code
- primitive_obsession: Overuse of primitives instead of objects
- shotgun_surgery: Changes requiring edits in many places
- magic_numbers: Numeric literals that should be named constants
- message_chains: Long method call chains (Law of Demeter violations)
- global_data: Module-level mutable data
- speculative_generality: Abstract classes with only one subclass
- parallel_inheritance: Parallel inheritance hierarchies
- alternative_interfaces: Classes with similar behavior but different APIs
- flag_arguments: Boolean parameters controlling function behavior
- setting_methods: Excessive setter methods
- trivial_commands: Trivial command objects that should be functions
- undocumented_code: Public classes/functions without docstrings
- duplicate_names: Duplicate entity names across modules
"""

from .long_methods import long_methods
from .long_parameter_list import long_parameter_list
from .god_class import god_class
from .data_class import data_class
from .feature_envy import feature_envy
from .dead_code import dead_code
from .primitive_obsession import primitive_obsession
from .shotgun_surgery import shotgun_surgery
from .magic_numbers import magic_numbers
from .message_chains import message_chains
from .global_data import global_data
from .speculative_generality import speculative_generality
from .parallel_inheritance import parallel_inheritance
from .alternative_interfaces import alternative_interfaces
from .flag_arguments import flag_arguments
from .setting_methods import setting_methods
from .trivial_commands import trivial_commands
from .undocumented_code import undocumented_code
from .duplicate_names import duplicate_names

# Alias for backwards compatibility
large_classes = god_class

__all__ = [
    "large_classes",
    "long_methods",
    "long_parameter_list",
    "god_class",
    "data_class",
    "feature_envy",
    "dead_code",
    "primitive_obsession",
    "shotgun_surgery",
    # New detectors
    "magic_numbers",
    "message_chains",
    "global_data",
    "speculative_generality",
    "parallel_inheritance",
    "alternative_interfaces",
    "flag_arguments",
    "setting_methods",
    "trivial_commands",
    "undocumented_code",
    "duplicate_names",
]

"""
CADSL Tools - Code Analysis DSL Tool Collection.

This package contains all code analysis tools implemented using the CADSL framework:

- inspection: Read-only code inspection queries (26 tools)
- smells: Code smell detectors (12 detectors)
- refactoring: Refactoring opportunity detectors (12 detectors)
- inheritance: Inheritance refactoring detectors (6 detectors)
- exceptions: Exception handling detectors (5 detectors)
- patterns: Design pattern detectors (6 detectors)
- testing: Test coverage detectors (10 detectors)
- dependencies: Dependency analysis detectors (3 detectors)
- rag: RAG-based semantic detectors (3 detectors)
- diagrams: UML and visualization generators (6 diagrams)

All tools use language-agnostic placeholders like {Class}, {Method} that
are resolved at runtime based on the context language setting.

Usage:
    from codeine.dsl.tools import list_modules, large_classes
    from codeine.dsl.tools.inspection import describe_class
    from codeine.dsl.tools.smells import god_class
    from codeine.dsl.tools.refactoring import extract_method
    from codeine.dsl.tools.testing import untested_classes
    from codeine.dsl.tools.diagrams import class_diagram
"""

from . import inspection
from . import smells
from . import refactoring
from . import inheritance
from . import exceptions
from . import patterns
from . import testing
from . import dependencies
from . import rag
from . import diagrams

# Re-export all tools for convenience
from .inspection import *
from .smells import *
from .refactoring import *
from .inheritance import *
from .exceptions import *
from .patterns import *
from .testing import *
from .dependencies import *
from .rag import *
from .diagrams import *

__all__ = (
    inspection.__all__ +
    smells.__all__ +
    refactoring.__all__ +
    inheritance.__all__ +
    exceptions.__all__ +
    patterns.__all__ +
    testing.__all__ +
    dependencies.__all__ +
    rag.__all__ +
    diagrams.__all__
)

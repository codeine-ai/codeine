"""
CADSL Step Classes.

This package contains all pipeline step implementations for CADSL.
Steps are extracted from transformer.py to reduce file size.

Step categories:
- conditional: WhenStep, UnlessStep, BranchStep, CatchStep
- data_flow: ParallelStep, CollectStep, NestStep (TODO)
- graph: GraphCyclesStep, GraphClosureStep, GraphTraverseStep (TODO)
- render: RenderTableStep, RenderChartStep, RenderMermaidStep (TODO)
- transform: PivotStep, ComputeStep (TODO)
- join: JoinStep, MergeSource, CrossJoinStep (TODO)
- similarity: SetSimilarityStep, StringMatchStep (TODO)
- integration: RagEnrichStep, CreateTaskStep, PythonStep (TODO)
"""

from .conditional import (
    WhenStep,
    UnlessStep,
    BranchStep,
    CatchStep,
)
from .graph import (
    GraphCyclesStep,
    GraphClosureStep,
    GraphTraverseStep,
    ParallelStep,
)
from .data_flow import (
    CollectStep,
    NestStep,
)

__all__ = [
    # Conditional steps
    "WhenStep",
    "UnlessStep",
    "BranchStep",
    "CatchStep",
    # Graph steps
    "GraphCyclesStep",
    "GraphClosureStep",
    "GraphTraverseStep",
    "ParallelStep",
    # Data flow steps
    "CollectStep",
    "NestStep",
]

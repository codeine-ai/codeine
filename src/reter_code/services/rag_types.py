"""
RAG Types - Data classes for RAG index operations.

Contains value objects used by RAGIndexManager and related components.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class LanguageSourceChanges:
    """
    Source changes for a single language type.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a value-object.

    Groups changed and deleted source IDs for one language.
    """
    changed: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)


@dataclass
class SyncChanges:
    """
    All source changes for RAG index synchronization.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a value-object.

    Consolidates 12 individual parameters (6 languages × 2 change types)
    into a structured object organized by language.
    """
    python: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)
    javascript: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)
    html: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)
    csharp: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)
    cpp: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)
    markdown: LanguageSourceChanges = field(default_factory=LanguageSourceChanges)

    @classmethod
    def from_params(
        cls,
        changed_python_sources: Optional[List[str]] = None,
        deleted_python_sources: Optional[List[str]] = None,
        changed_javascript_sources: Optional[List[str]] = None,
        deleted_javascript_sources: Optional[List[str]] = None,
        changed_html_sources: Optional[List[str]] = None,
        deleted_html_sources: Optional[List[str]] = None,
        changed_csharp_sources: Optional[List[str]] = None,
        deleted_csharp_sources: Optional[List[str]] = None,
        changed_cpp_sources: Optional[List[str]] = None,
        deleted_cpp_sources: Optional[List[str]] = None,
        changed_markdown_files: Optional[List[str]] = None,
        deleted_markdown_files: Optional[List[str]] = None,
    ) -> "SyncChanges":
        """Create SyncChanges from individual parameters for backward compatibility."""
        return cls(
            python=LanguageSourceChanges(
                changed=changed_python_sources or [],
                deleted=deleted_python_sources or [],
            ),
            javascript=LanguageSourceChanges(
                changed=changed_javascript_sources or [],
                deleted=deleted_javascript_sources or [],
            ),
            html=LanguageSourceChanges(
                changed=changed_html_sources or [],
                deleted=deleted_html_sources or [],
            ),
            csharp=LanguageSourceChanges(
                changed=changed_csharp_sources or [],
                deleted=deleted_csharp_sources or [],
            ),
            cpp=LanguageSourceChanges(
                changed=changed_cpp_sources or [],
                deleted=deleted_cpp_sources or [],
            ),
            markdown=LanguageSourceChanges(
                changed=changed_markdown_files or [],
                deleted=deleted_markdown_files or [],
            ),
        )

    def has_changes(self) -> bool:
        """Check if there are any changes to sync."""
        return any([
            self.python.changed, self.python.deleted,
            self.javascript.changed, self.javascript.deleted,
            self.html.changed, self.html.deleted,
            self.csharp.changed, self.csharp.deleted,
            self.cpp.changed, self.cpp.deleted,
            self.markdown.changed, self.markdown.deleted,
        ])


class RAGSearchResult:
    """
    Result from a RAG semantic search.

    @reter-cnl: This is-in-layer Utility-Layer.
    @reter-cnl: This is a value-object.
    """

    def __init__(
        self,
        entity_type: str,
        name: str,
        qualified_name: str,
        file: str,
        line: int,
        end_line: Optional[int],
        score: float,
        source_type: str,  # "python", "javascript", "html", "csharp", or "markdown"
        docstring: Optional[str] = None,
        content_preview: Optional[str] = None,
        content: Optional[str] = None,
        heading: Optional[str] = None,
        language: Optional[str] = None,
        class_name: Optional[str] = None
    ):
        self.entity_type = entity_type
        self.name = name
        self.qualified_name = qualified_name
        self.file = file
        self.line = line
        self.end_line = end_line
        self.score = score
        self.source_type = source_type
        self.docstring = docstring
        self.content_preview = content_preview
        self.content = content
        self.heading = heading
        self.language = language
        self.class_name = class_name

    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "entity_type": self.entity_type,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "score": round(self.score, 4),
            "source_type": self.source_type,
        }

        if self.docstring:
            result["docstring"] = self.docstring
        if self.content_preview:
            result["content_preview"] = self.content_preview
        if self.heading:
            result["heading"] = self.heading
        if self.language:
            result["language"] = self.language
        if self.class_name:
            result["class_name"] = self.class_name
        if include_content and self.content:
            result["content"] = self.content

        return result

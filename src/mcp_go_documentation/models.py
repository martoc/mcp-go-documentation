"""Data models for Go documentation."""

from dataclasses import dataclass


@dataclass
class DocumentMetadata:
    """Metadata extracted from markdown frontmatter or HTML comment headers."""

    title: str
    description: str | None = None


@dataclass
class Document:
    """Represents a documentation page."""

    path: str
    title: str
    description: str | None
    section: str
    content: str
    url: str


@dataclass
class SearchResult:
    """Represents a search result."""

    path: str
    title: str
    url: str
    snippet: str
    score: float
    section: str

"""Tests for data models."""

from mcp_go_documentation.models import Document, DocumentMetadata, SearchResult


def test_document_metadata_creation() -> None:
    """Test creating a DocumentMetadata instance."""
    metadata = DocumentMetadata(
        title="Effective Go",
        description="A guide for writing idiomatic Go",
    )
    assert metadata.title == "Effective Go"
    assert metadata.description == "A guide for writing idiomatic Go"


def test_document_metadata_optional_fields() -> None:
    """Test DocumentMetadata with optional fields."""
    metadata = DocumentMetadata(title="Effective Go")
    assert metadata.title == "Effective Go"
    assert metadata.description is None


def test_document_creation() -> None:
    """Test creating a Document instance."""
    doc = Document(
        path="doc/effective_go.html",
        title="Effective Go",
        description="A guide for writing idiomatic Go",
        section="doc",
        content="Effective Go content",
        url="https://go.dev/doc/effective_go",
    )
    assert doc.path == "doc/effective_go.html"
    assert doc.title == "Effective Go"
    assert doc.section == "doc"
    assert "Effective Go content" in doc.content


def test_search_result_creation() -> None:
    """Test creating a SearchResult instance."""
    result = SearchResult(
        path="doc/effective_go.html",
        title="Effective Go",
        url="https://go.dev/doc/effective_go",
        snippet="...idiomatic Go style...",
        score=12.5,
        section="doc",
    )
    assert result.path == "doc/effective_go.html"
    assert result.score == 12.5
    assert result.section == "doc"

"""Tests for database operations."""

import tempfile
from pathlib import Path

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.models import Document


def test_database_initialisation() -> None:
    """Test database initialisation creates schema."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)
        assert db.db_path == db_path
        assert db_path.exists()


def test_upsert_document() -> None:
    """Test inserting and updating a document."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        doc = Document(
            path="doc/effective_go.html",
            title="Effective Go",
            description="Guide for writing idiomatic Go",
            section="doc",
            content="Content about idiomatic Go programming",
            url="https://go.dev/doc/effective_go",
        )

        db.upsert_document(doc)
        retrieved = db.get_document("doc/effective_go.html")

        assert retrieved is not None
        assert retrieved.title == "Effective Go"
        assert retrieved.content == "Content about idiomatic Go programming"


def test_upsert_document_update() -> None:
    """Test updating an existing document."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        doc1 = Document(
            path="doc/effective_go.html",
            title="Original",
            description=None,
            section="doc",
            content="Original content",
            url="https://go.dev/doc/effective_go",
        )
        db.upsert_document(doc1)

        doc2 = Document(
            path="doc/effective_go.html",
            title="Updated",
            description=None,
            section="doc",
            content="Updated content",
            url="https://go.dev/doc/effective_go",
        )
        db.upsert_document(doc2)

        retrieved = db.get_document("doc/effective_go.html")
        assert retrieved is not None
        assert retrieved.title == "Updated"
        assert retrieved.content == "Updated content"


def test_search_documents() -> None:
    """Test searching documents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        doc1 = Document(
            path="doc1.md",
            title="Go Modules",
            description="Modules guide",
            section="ref",
            content="This document covers Go module management",
            url="https://go.dev/ref/mod",
        )
        doc2 = Document(
            path="doc2.md",
            title="Go Concurrency",
            description="Concurrency primer",
            section="doc",
            content="This document covers Go goroutines and channels",
            url="https://go.dev/doc/concurrency",
        )

        db.upsert_document(doc1)
        db.upsert_document(doc2)

        results = db.search("module")
        assert len(results) > 0
        assert any("Modules" in r.title for r in results)


def test_search_with_section_filter() -> None:
    """Test searching with a section filter."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        doc1 = Document(
            path="doc1.md",
            title="Go Concurrency",
            description=None,
            section="doc",
            content="Goroutines and channels documentation",
            url="https://go.dev/doc/concurrency",
        )
        doc2 = Document(
            path="doc2.md",
            title="Go Concurrency Blog",
            description=None,
            section="blog",
            content="Blog post about Go concurrency",
            url="https://go.dev/blog/concurrency",
        )

        db.upsert_document(doc1)
        db.upsert_document(doc2)

        results = db.search("concurrency", section="doc")
        assert len(results) == 1
        assert results[0].section == "doc"


def test_get_document_not_found() -> None:
    """Test getting a non-existent document."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        result = db.get_document("nonexistent.md")
        assert result is None


def test_clear_database() -> None:
    """Test clearing all documents."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        doc = Document(
            path="test.md",
            title="Test",
            description=None,
            section="doc",
            content="Content",
            url="https://go.dev/doc/test",
        )
        db.upsert_document(doc)

        assert db.get_document_count() == 1

        db.clear()

        assert db.get_document_count() == 0


def test_get_document_count() -> None:
    """Test getting the document count."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "test.db"
        db = DocumentDatabase(db_path)

        assert db.get_document_count() == 0

        for i in range(5):
            doc = Document(
                path=f"doc{i}.md",
                title=f"Doc {i}",
                description=None,
                section="doc",
                content=f"Content {i}",
                url=f"https://go.dev/doc/doc{i}",
            )
            db.upsert_document(doc)

        assert db.get_document_count() == 5

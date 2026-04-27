"""Tests for the indexer."""

import tempfile
from pathlib import Path

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.indexer import GoDocsIndexer


def test_index_from_path_indexes_supported_files() -> None:
    """Test that indexing a local checkout walks markdown and HTML files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        content_path = repo_path / "_content"
        (content_path / "doc").mkdir(parents=True)
        (content_path / "blog").mkdir(parents=True)
        (content_path / "images").mkdir(parents=True)

        (content_path / "doc" / "effective_go.html").write_text(
            '<!--{"Title": "Effective Go"}-->\n<p>Idiomatic Go.</p>'
        )
        (content_path / "blog" / "intro-generics.md").write_text(
            "---\ntitle: Generics Intro\n---\nGenerics body.\n"
        )
        (content_path / "menus.yaml").write_text("- item: skipped")
        (content_path / "images" / "should-be-skipped.html").write_text(
            "<p>This asset directory should be skipped.</p>"
        )

        db_path = repo_path / "test.db"
        database = DocumentDatabase(db_path)
        indexer = GoDocsIndexer(database)

        count = indexer.index_from_path(repo_path)

        assert count == 2
        assert database.get_document_count() == 2

        effective_go = database.get_document("doc/effective_go.html")
        assert effective_go is not None
        assert effective_go.title == "Effective Go"

        generics = database.get_document("blog/intro-generics.md")
        assert generics is not None
        assert generics.title == "Generics Intro"


def test_index_from_path_missing_content_directory_raises() -> None:
    """Test that an indexing failure surfaces a descriptive error."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_path = Path(temp_dir)
        db_path = repo_path / "test.db"
        database = DocumentDatabase(db_path)
        indexer = GoDocsIndexer(database)

        try:
            indexer.index_from_path(repo_path)
        except ValueError as exc:
            assert "Content path does not exist" in str(exc)
        else:  # pragma: no cover - guard for the assertion failure path
            raise AssertionError("Expected ValueError when _content is missing")


def test_collect_files_skips_excluded_directories() -> None:
    """Test that the file collector skips known asset directories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        content_path = Path(temp_dir)
        (content_path / "css").mkdir()
        (content_path / "doc").mkdir()
        (content_path / "css" / "style.html").write_text("<p>skip me</p>")
        (content_path / "doc" / "keep.md").write_text("---\ntitle: Keep\n---\nKeep me.")

        db_path = content_path / "test.db"
        database = DocumentDatabase(db_path)
        indexer = GoDocsIndexer(database)

        files = indexer._collect_files(content_path)
        assert len(files) == 1
        assert files[0].name == "keep.md"

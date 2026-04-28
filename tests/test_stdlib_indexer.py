"""Tests for the standard library indexer."""

import tempfile
from pathlib import Path

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.indexer import GoStdlibIndexer


def _make_repo(tmp_path: Path) -> Path:
    """Create a minimal ``golang/go``-shaped repository on disk for tests."""
    src = tmp_path / "src"

    fmt_dir = src / "fmt"
    fmt_dir.mkdir(parents=True)
    (fmt_dir / "doc.go").write_text(
        "// Package fmt implements formatted I/O.\n"
        "package fmt\n"
    )
    (fmt_dir / "print.go").write_text(
        "package fmt\n"
        "\n"
        "// Println prints args to stdout.\n"
        "func Println(args ...any) (int, error) { return 0, nil }\n"
    )

    nethttp_dir = src / "net" / "http"
    nethttp_dir.mkdir(parents=True)
    (nethttp_dir / "server.go").write_text(
        "// Package http provides HTTP client and server implementations.\n"
        "package http\n"
        "\n"
        "// ListenAndServe starts an HTTP server.\n"
        "func ListenAndServe(addr string, handler Handler) error { return nil }\n"
    )

    cmd_dir = src / "cmd" / "compile"
    cmd_dir.mkdir(parents=True)
    (cmd_dir / "main.go").write_text(
        "// Cmd compile is the Go compiler.\n"
        "package main\n"
        "\n"
        "func main() {}\n"
    )

    vendor_dir = src / "vendor" / "example.com" / "lib"
    vendor_dir.mkdir(parents=True)
    (vendor_dir / "lib.go").write_text(
        "package lib\n"
        "\n"
        "func Helper() {}\n"
    )

    testdata_dir = src / "fmt" / "testdata"
    testdata_dir.mkdir(parents=True)
    (testdata_dir / "fixture.go").write_text(
        "package testdata\n"
        "\n"
        "func Fixture() {}\n"
    )

    return tmp_path


def test_index_from_path_indexes_stdlib_packages(tmp_path: Path) -> None:
    """The indexer walks ``src/`` and stores one document per package."""
    repo = _make_repo(tmp_path)
    db_path = tmp_path / "test.db"
    database = DocumentDatabase(db_path)
    indexer = GoStdlibIndexer(database)

    count = indexer.index_from_path(repo)

    assert count == 2
    assert database.get_document_count() == 2

    fmt_doc = database.get_document("std/fmt")
    assert fmt_doc is not None
    assert fmt_doc.section == "std"
    assert fmt_doc.url == "https://pkg.go.dev/fmt"
    assert "Package fmt implements formatted I/O." in fmt_doc.content
    assert "Println" in fmt_doc.content

    http_doc = database.get_document("std/net/http")
    assert http_doc is not None
    assert http_doc.url == "https://pkg.go.dev/net/http"
    assert "ListenAndServe" in http_doc.content


def test_index_skips_cmd_vendor_and_testdata(tmp_path: Path) -> None:
    """``cmd/``, ``vendor/`` and any ``testdata`` subtree are excluded."""
    repo = _make_repo(tmp_path)
    db_path = tmp_path / "test.db"
    database = DocumentDatabase(db_path)
    indexer = GoStdlibIndexer(database)
    indexer.index_from_path(repo)

    assert database.get_document("std/cmd/compile") is None
    assert database.get_document("std/vendor/example.com/lib") is None
    assert database.get_document("std/fmt/testdata") is None


def test_index_from_path_missing_src_raises() -> None:
    """A missing ``src/`` directory surfaces a descriptive ``ValueError``."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir)
        db_path = repo / "test.db"
        database = DocumentDatabase(db_path)
        indexer = GoStdlibIndexer(database)

        try:
            indexer.index_from_path(repo)
        except ValueError as exc:
            assert "Source path does not exist" in str(exc)
        else:  # pragma: no cover - guard for assertion path
            raise AssertionError("Expected ValueError when src/ is missing")


def test_clear_section_only_removes_stdlib(tmp_path: Path) -> None:
    """``DocumentDatabase.clear_section`` scopes deletion to a single section."""
    db_path = tmp_path / "test.db"
    database = DocumentDatabase(db_path)

    from mcp_go_documentation.models import Document

    database.upsert_document(
        Document(
            path="doc/effective_go.html",
            title="Effective Go",
            description=None,
            section="doc",
            content="Stay effective.",
            url="https://go.dev/doc/effective_go",
        )
    )
    database.upsert_document(
        Document(
            path="std/fmt",
            title="fmt - fmt",
            description=None,
            section="std",
            content="package fmt",
            url="https://pkg.go.dev/fmt",
        )
    )

    assert database.get_document_count() == 2
    database.clear_section("std")
    assert database.get_document_count() == 1
    assert database.get_document("doc/effective_go.html") is not None
    assert database.get_document("std/fmt") is None

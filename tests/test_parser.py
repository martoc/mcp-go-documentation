"""Tests for the document parser."""

import tempfile
from pathlib import Path

from mcp_go_documentation.parser import DocumentParser


def test_extract_section_root() -> None:
    """Test extracting the section from a root-level file."""
    parser = DocumentParser()
    section = parser._extract_section(Path("about.md"))
    assert section == "root"


def test_extract_section_nested() -> None:
    """Test extracting the section from a nested file."""
    parser = DocumentParser()
    section = parser._extract_section(Path("doc/effective_go.html"))
    assert section == "doc"


def test_compute_url_regular_markdown() -> None:
    """Test computing the URL for a regular markdown file."""
    parser = DocumentParser()
    url = parser._compute_url(Path("blog/intro-generics.md"))
    assert url == "https://go.dev/blog/intro-generics"


def test_compute_url_regular_html() -> None:
    """Test computing the URL for an HTML file."""
    parser = DocumentParser()
    url = parser._compute_url(Path("doc/effective_go.html"))
    assert url == "https://go.dev/doc/effective_go"


def test_compute_url_index_file() -> None:
    """Test computing the URL for an index.md file collapses to its directory."""
    parser = DocumentParser()
    url = parser._compute_url(Path("doc/database/index.md"))
    assert url == "https://go.dev/doc/database"


def test_compute_url_root_index() -> None:
    """Test computing the URL for the root index.md."""
    parser = DocumentParser()
    url = parser._compute_url(Path("index.md"))
    assert url == "https://go.dev/"


def test_clean_markdown_content_strips_html_tags() -> None:
    """Test that markdown cleaning strips embedded HTML tags."""
    parser = DocumentParser()
    content = "Some <b>bold</b> text and a <a href='/x'>link</a>."
    cleaned = parser._clean_markdown_content(content)
    assert "<" not in cleaned
    assert "bold" in cleaned
    assert "link" in cleaned


def test_clean_markdown_content_removes_html_comments() -> None:
    """Test that markdown cleaning removes HTML comments."""
    parser = DocumentParser()
    content = "<!-- TODO -->\nReal content here."
    cleaned = parser._clean_markdown_content(content)
    assert "<!--" not in cleaned
    assert "Real content here." in cleaned


def test_clean_html_content_strips_scripts_and_styles() -> None:
    """Test that HTML cleaning removes script and style blocks."""
    parser = DocumentParser()
    content = (
        "<style>body { color: red; }</style>"
        "<script>alert('x');</script>"
        "<p>Hello world.</p>"
    )
    cleaned = parser._clean_html_content(content)
    assert "alert" not in cleaned
    assert "color: red" not in cleaned
    assert "Hello world." in cleaned


def test_extract_html_metadata_block_valid() -> None:
    """Test extracting JSON metadata from an HTML comment block."""
    parser = DocumentParser()
    raw = '<!--{\n  "Title": "Effective Go",\n  "Template": true\n}-->\n<p>Body</p>'
    metadata, body = parser._extract_html_metadata_block(raw)
    assert metadata.get("Title") == "Effective Go"
    assert metadata.get("Template") is True
    assert "<p>Body</p>" in body


def test_extract_html_metadata_block_missing() -> None:
    """Test that missing metadata returns an empty dict and the original body."""
    parser = DocumentParser()
    raw = "<p>Body without metadata</p>"
    metadata, body = parser._extract_html_metadata_block(raw)
    assert metadata == {}
    assert body == raw


def test_parse_markdown_file_with_frontmatter() -> None:
    """Test parsing a markdown file with YAML frontmatter."""
    parser = DocumentParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        file_path = base_path / "blog" / "intro-generics.md"
        file_path.parent.mkdir(parents=True)

        content = """---
title: An Introduction To Generics
summary: A primer on Go generics.
---

# Generics

This is a test.
"""
        file_path.write_text(content)

        doc = parser.parse_file(file_path, base_path)

        assert doc is not None
        assert doc.title == "An Introduction To Generics"
        assert doc.description == "A primer on Go generics."
        assert "Generics" in doc.content
        assert doc.path == "blog/intro-generics.md"
        assert doc.section == "blog"
        assert doc.url == "https://go.dev/blog/intro-generics"


def test_parse_markdown_file_without_frontmatter() -> None:
    """Test parsing a markdown file without frontmatter falls back to filename."""
    parser = DocumentParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        file_path = base_path / "test-file.md"

        file_path.write_text("# Test Content\n\nBody text.")

        doc = parser.parse_file(file_path, base_path)

        assert doc is not None
        assert doc.title == "Test File"
        assert "Test Content" in doc.content


def test_parse_html_file_with_metadata() -> None:
    """Test parsing an HTML file with JSON metadata in a leading comment."""
    parser = DocumentParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        file_path = base_path / "doc" / "effective_go.html"
        file_path.parent.mkdir(parents=True)

        file_path.write_text(
            '<!--{\n\t"Title": "Effective Go",\n\t"Template": true\n}-->\n'
            "<h2>Introduction</h2>\n<p>Go is an open-source language.</p>"
        )

        doc = parser.parse_file(file_path, base_path)

        assert doc is not None
        assert doc.title == "Effective Go"
        assert "Introduction" in doc.content
        assert "Go is an open-source language." in doc.content
        assert doc.path == "doc/effective_go.html"
        assert doc.section == "doc"
        assert doc.url == "https://go.dev/doc/effective_go"


def test_parse_html_file_without_metadata() -> None:
    """Test parsing an HTML file without a metadata block falls back to filename."""
    parser = DocumentParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        file_path = base_path / "rebuild.html"

        file_path.write_text("<p>Rebuild instructions.</p>")

        doc = parser.parse_file(file_path, base_path)

        assert doc is not None
        assert doc.title == "Rebuild"
        assert "Rebuild instructions." in doc.content


def test_parse_unsupported_extension_returns_none() -> None:
    """Test that unsupported file extensions are ignored."""
    parser = DocumentParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        base_path = Path(temp_dir)
        file_path = base_path / "menu.yaml"
        file_path.write_text("- item: value")

        doc = parser.parse_file(file_path, base_path)
        assert doc is None

"""Tests for the Go source-code parser."""

from pathlib import Path

from mcp_go_documentation.go_source_parser import GoPackage, GoSourceParser


def test_parse_file_extracts_package_doc_and_name() -> None:
    """A package's leading ``//`` comment block becomes the package doc."""
    parser = GoSourceParser()
    source = (
        "// Package fmt implements formatted I/O.\n"
        "// It mirrors the C printf and scanf families.\n"
        "package fmt\n"
    )
    name, doc, decls = parser.parse_file(source)
    assert name == "fmt"
    assert "Package fmt implements formatted I/O." in doc
    assert "C printf and scanf families." in doc
    assert decls == []


def test_parse_file_extracts_block_package_doc() -> None:
    """``/* ... */`` package comments are also captured."""
    parser = GoSourceParser()
    source = (
        "/*\n"
        "Package math provides basic constants and mathematical functions.\n"
        "*/\n"
        "package math\n"
    )
    name, doc, _ = parser.parse_file(source)
    assert name == "math"
    assert "Package math provides basic constants" in doc


def test_parse_file_skips_build_directives_in_doc() -> None:
    """Build directives such as ``//go:build`` are not treated as documentation."""
    parser = GoSourceParser()
    source = (
        "//go:build linux\n"
        "// +build linux\n"
        "\n"
        "// Package linux provides Linux-specific helpers.\n"
        "package linux\n"
    )
    name, doc, _ = parser.parse_file(source)
    assert name == "linux"
    assert "go:build" not in doc
    assert "+build" not in doc
    assert "Package linux provides" in doc


def test_parse_file_extracts_exported_functions() -> None:
    """Exported functions and their doc comments are captured."""
    parser = GoSourceParser()
    source = (
        "// Package widget exposes widget helpers.\n"
        "package widget\n"
        "\n"
        "// Println prints a line to stdout.\n"
        "func Println(a ...any) (int, error) {\n"
        "    return 0, nil\n"
        "}\n"
        "\n"
        "// internal helper, unexported\n"
        "func helper() {}\n"
    )
    _, _, decls = parser.parse_file(source)
    assert len(decls) == 1
    decl = decls[0]
    assert decl.kind == "func"
    assert decl.name == "Println"
    assert "prints a line" in decl.doc
    assert decl.signature.startswith("func Println")
    assert "{" not in decl.signature


def test_parse_file_captures_method_receiver() -> None:
    """Methods record their receiver expression."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "// Reset clears the buffer.\n"
        "func (b *Buffer) Reset() {\n"
        "    // body\n"
        "}\n"
    )
    _, _, decls = parser.parse_file(source)
    assert len(decls) == 1
    decl = decls[0]
    assert decl.name == "Reset"
    assert decl.receiver == "b *Buffer"


def test_parse_grouped_const_declaration() -> None:
    """Grouped ``const`` declarations expose each entry separately."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "const (\n"
        "    // First sentinel value.\n"
        "    First = 1\n"
        "    // Second sentinel value.\n"
        "    Second = 2\n"
        "    third = 3 // unexported\n"
        ")\n"
    )
    _, _, decls = parser.parse_file(source)
    names = {d.name for d in decls}
    assert names == {"First", "Second"}
    assert all(d.kind == "const" for d in decls)
    first = next(d for d in decls if d.name == "First")
    assert "First sentinel value" in first.doc


def test_parse_grouped_type_declaration() -> None:
    """Grouped ``type`` declarations are decomposed into individual types."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "type (\n"
        "    // Reader reads bytes.\n"
        "    Reader interface{ Read([]byte) (int, error) }\n"
        "    // Writer writes bytes.\n"
        "    Writer interface{ Write([]byte) (int, error) }\n"
        ")\n"
    )
    _, _, decls = parser.parse_file(source)
    names = {d.name for d in decls}
    assert names == {"Reader", "Writer"}
    assert all(d.kind == "type" for d in decls)


def test_parse_top_level_type_with_struct_body() -> None:
    """``type Foo struct { ... }`` captures only the signature, not the body."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "// Buffer is a growable byte buffer.\n"
        "type Buffer struct {\n"
        "    data []byte\n"
        "}\n"
        "\n"
        "// Hidden is unexported.\n"
        "type hidden struct{}\n"
    )
    _, _, decls = parser.parse_file(source)
    assert len(decls) == 1
    decl = decls[0]
    assert decl.kind == "type"
    assert decl.name == "Buffer"
    assert "{" not in decl.signature


def test_parse_skips_string_literals_when_balancing_parens() -> None:
    """String literals containing parens or braces don't confuse the scanner."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "// Greet returns a greeting.\n"
        "func Greet(name string) string {\n"
        '    return "hello (" + name + ") {!}"\n'
        "}\n"
    )
    _, _, decls = parser.parse_file(source)
    assert len(decls) == 1
    assert decls[0].name == "Greet"


def test_parse_package_aggregates_files(tmp_path: Path) -> None:
    """Multiple files in a package combine into a single ``GoPackage``."""
    parser = GoSourceParser()
    pkg_dir = tmp_path / "fmt"
    pkg_dir.mkdir()
    (pkg_dir / "doc.go").write_text(
        "// Package fmt implements formatted I/O.\n"
        "package fmt\n"
    )
    (pkg_dir / "print.go").write_text(
        "package fmt\n"
        "\n"
        "// Println prints a line.\n"
        "func Println(args ...any) (int, error) { return 0, nil }\n"
    )
    (pkg_dir / "print_test.go").write_text(
        "package fmt\n"
        "\n"
        "// PrintTest should be ignored.\n"
        "func TestPrintln(t *testing.T) {}\n"
    )
    package = parser.parse_package(pkg_dir, "fmt")
    assert package is not None
    assert package.name == "fmt"
    assert "Package fmt implements formatted I/O." in package.doc
    names = {d.name for d in package.declarations}
    assert "Println" in names
    assert "TestPrintln" not in names


def test_render_markdown_includes_doc_and_signatures() -> None:
    """The rendered markdown contains package doc, index and per-decl blocks."""
    parser = GoSourceParser()
    source = (
        "// Package widget exposes widget helpers.\n"
        "package widget\n"
        "\n"
        "// Println prints a line.\n"
        "func Println() {}\n"
    )
    name, doc, decls = parser.parse_file(source)
    assert name is not None
    package = GoPackage(name=name, import_path="widget", doc=doc, declarations=decls)
    rendered = parser.render_markdown(package)
    assert "# Package widget" in rendered
    assert "## Index" in rendered
    assert "Println" in rendered
    assert "prints a line" in rendered


def test_parse_package_returns_none_for_empty_dir(tmp_path: Path) -> None:
    """Directories with no Go source files yield ``None``."""
    parser = GoSourceParser()
    empty = tmp_path / "empty"
    empty.mkdir()
    assert parser.parse_package(empty, "empty") is None


def test_parse_package_returns_none_when_only_tests(tmp_path: Path) -> None:
    """Directories with only ``_test.go`` files are not packages for our purposes."""
    parser = GoSourceParser()
    pkg_dir = tmp_path / "tests"
    pkg_dir.mkdir()
    (pkg_dir / "all_test.go").write_text("package tests\n")
    assert parser.parse_package(pkg_dir, "tests") is None


def test_parse_var_with_type() -> None:
    """Single-line ``var Name Type = value`` declarations are captured."""
    parser = GoSourceParser()
    source = (
        "package widget\n"
        "\n"
        "// ErrClosed is returned when the widget is closed.\n"
        "var ErrClosed = errors.New(\"closed\")\n"
    )
    _, _, decls = parser.parse_file(source)
    assert any(d.kind == "var" and d.name == "ErrClosed" for d in decls)


def test_string_and_comment_stripper_keeps_length() -> None:
    """Stripper preserves indices for downstream regex/scanning logic."""
    parser = GoSourceParser()
    line = 'foo("hello /* not comment */", x) // trailing'
    sanitised = parser._strip_strings_and_comments(line)
    assert len(sanitised) == len(line)
    assert "/*" not in sanitised.replace(" ", "X")
    assert "//" not in sanitised
    assert "(" in sanitised

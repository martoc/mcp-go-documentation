"""Parser for Go source files that extracts godoc-style documentation.

The standard library is published as Go source files; ``pkg.go.dev`` renders
package documentation from the doc comments above ``package`` declarations
and exported top-level declarations.  This module performs a pragmatic,
line-based extraction of those constructs without requiring the Go toolchain.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

_DECL_KEYWORDS: frozenset[str] = frozenset({"func", "type", "const", "var"})

_BUILD_DIRECTIVE_PREFIXES: tuple[str, ...] = (
    "go:",
    "+build",
    "export ",
    "line ",
    "cgo:",
)


@dataclass
class GoDeclaration:
    """A top-level Go declaration with its associated doc comment."""

    kind: str
    name: str
    signature: str
    doc: str
    receiver: str | None = None


@dataclass
class GoPackage:
    """A Go package extracted from one or more source files."""

    name: str
    import_path: str
    doc: str
    declarations: list[GoDeclaration] = field(default_factory=list)


class GoSourceParser:
    """Extracts package and exported declaration documentation from Go source.

    The parser is intentionally line-oriented: it walks the file once and
    treats contiguous ``//`` (or ``/* ... */``) comments immediately preceding
    a ``package`` keyword or top-level declaration as the doc comment for that
    construct, mirroring the convention used by ``go/doc``.
    """

    PACKAGE_LINE_RE = re.compile(r"^package\s+(\w+)")
    FUNC_NAME_RE = re.compile(
        r"^func\s+(?:\((?P<recv>[^)]*)\)\s+)?(?P<name>\w+)\s*"
    )
    SIMPLE_NAME_RE = re.compile(r"^(?P<name>\w+)")
    TYPE_NAME_RE = re.compile(r"^(?P<name>\w+)(?:\s*\[[^\]]*\])?\s*(?P<rest>.*)")

    def parse_package(self, package_dir: Path, import_path: str) -> GoPackage | None:
        """Parse all non-test ``*.go`` files in *package_dir* into a package.

        Args:
            package_dir: Directory containing the package source files.
            import_path: Canonical import path (for example ``net/http``).

        Returns:
            ``GoPackage`` instance, or ``None`` if no Go source files are
            present or no ``package`` declaration could be found.
        """
        files = sorted(
            p
            for p in package_dir.glob("*.go")
            if not p.name.endswith("_test.go")
        )
        if not files:
            return None

        package_name: str | None = None
        package_docs: list[str] = []
        declarations: list[GoDeclaration] = []

        for file_path in files:
            try:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            file_pkg, file_doc, file_decls = self.parse_file(text)
            if file_pkg is None:
                continue
            if package_name is None:
                package_name = file_pkg
            if file_doc and file_doc not in package_docs:
                package_docs.append(file_doc)
            declarations.extend(file_decls)

        if package_name is None:
            return None

        return GoPackage(
            name=package_name,
            import_path=import_path,
            doc="\n\n".join(package_docs).strip(),
            declarations=self._sort_declarations(declarations),
        )

    def parse_file(self, text: str) -> tuple[str | None, str, list[GoDeclaration]]:
        """Parse a single Go source file.

        Args:
            text: Contents of the source file.

        Returns:
            Tuple of ``(package_name, package_doc, declarations)``.  The
            package name is ``None`` for files that do not declare a package
            (such as build-excluded files or fragments).
        """
        lines = text.splitlines()
        index = 0
        total = len(lines)
        package_name: str | None = None
        package_doc = ""
        declarations: list[GoDeclaration] = []
        pending_doc: list[str] = []
        seen_package = False

        while index < total:
            raw = lines[index]
            stripped = raw.strip()

            if not stripped:
                pending_doc = []
                index += 1
                continue

            if stripped.startswith("//"):
                pending_doc.extend(self._consume_line_comment_block(stripped))
                index += 1
                continue

            if stripped.startswith("/*"):
                cleaned, consumed = self._consume_block_comment(lines, index)
                if cleaned:
                    pending_doc.append(cleaned)
                index += consumed
                continue

            if not seen_package:
                match = self.PACKAGE_LINE_RE.match(stripped)
                if match:
                    package_name = match.group(1)
                    package_doc = "\n".join(pending_doc).strip()
                    pending_doc = []
                    seen_package = True
                    index += 1
                    continue

            first_word = stripped.split(None, 1)[0]

            if not raw[:1].isspace() and first_word in _DECL_KEYWORDS:
                after = stripped[len(first_word) :].lstrip()
                if first_word != "func" and after.startswith("("):
                    body, consumed = self._slurp_balanced_parens(lines, index)
                    declarations.extend(self._parse_group(first_word, body))
                    pending_doc = []
                    index += consumed
                    continue

                signature, consumed = self._slurp_signature(lines, index)
                decl = self._build_declaration(
                    kind=first_word,
                    signature=signature,
                    doc="\n".join(pending_doc).strip(),
                )
                if decl is not None:
                    declarations.append(decl)
                pending_doc = []
                index += consumed
                continue

            if not raw[:1].isspace() and first_word == "import":
                after = stripped[len("import") :].lstrip()
                if after.startswith("("):
                    _, consumed = self._slurp_balanced_parens(lines, index)
                    pending_doc = []
                    index += consumed
                    continue

            pending_doc = []
            index += 1

        return package_name, package_doc, declarations

    def _consume_line_comment_block(self, stripped: str) -> list[str]:
        """Extract the textual content from a ``//`` comment line.

        Build directives such as ``//go:build`` are silently dropped: they are
        not documentation.
        """
        content = stripped[2:]
        if content.startswith(" "):
            content = content[1:]
        if content.startswith(_BUILD_DIRECTIVE_PREFIXES):
            return []
        return [content]

    def _consume_block_comment(
        self, lines: list[str], start: int
    ) -> tuple[str, int]:
        """Consume a ``/* ... */`` block comment starting at *start*.

        Returns:
            Tuple of ``(cleaned text, lines consumed)``.
        """
        first = lines[start].lstrip()
        rest = first[2:]
        if "*/" in rest:
            inner = rest[: rest.index("*/")]
            cleaned = self._clean_block_comment_text([inner])
            return cleaned, 1

        buffer: list[str] = [rest]
        index = start + 1
        while index < len(lines):
            line = lines[index]
            if "*/" in line:
                buffer.append(line[: line.index("*/")])
                return self._clean_block_comment_text(buffer), index - start + 1
            buffer.append(line)
            index += 1
        return self._clean_block_comment_text(buffer), index - start

    def _clean_block_comment_text(self, lines: list[str]) -> str:
        """Normalise a block comment body to a paragraph-style string."""
        cleaned: list[str] = []
        for raw in lines:
            stripped = raw.strip()
            if stripped.startswith("*"):
                stripped = stripped[1:].lstrip()
            cleaned.append(stripped)
        while cleaned and not cleaned[0]:
            cleaned.pop(0)
        while cleaned and not cleaned[-1]:
            cleaned.pop()
        return "\n".join(cleaned)

    def _slurp_signature(
        self, lines: list[str], start: int
    ) -> tuple[str, int]:
        """Capture a single declaration's signature, dropping any body.

        The signature stops at the first ``{`` that is not within a string,
        balanced parentheses, or already-balanced brackets.  For declarations
        that span multiple lines (for example a function with split arguments)
        we keep slurping until parentheses balance.
        """
        depth = 0
        captured: list[str] = []
        index = start
        truncated_first_line: str | None = None

        while index < len(lines):
            line = lines[index]
            sanitised = self._strip_strings_and_comments(line)
            brace_position = self._find_unguarded_brace(line, sanitised)
            if brace_position is not None and depth == 0:
                truncated = line[:brace_position]
                if index == start:
                    truncated_first_line = truncated
                else:
                    captured.append(truncated)
                index += 1
                break

            captured.append(line)
            for ch in sanitised:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
            index += 1
            if depth == 0:
                break

        if truncated_first_line is not None:
            captured = [truncated_first_line]

        signature = "\n".join(captured).rstrip()
        return signature, index - start

    def _slurp_balanced_parens(
        self, lines: list[str], start: int
    ) -> tuple[str, int]:
        """Slurp the body of a parenthesised group, returning its inner text.

        The starting line is expected to contain the opening ``(``; the body
        is the content between that ``(`` and its matching ``)``.
        """
        first = lines[start]
        first_sanitised = self._strip_strings_and_comments(first)
        open_index = first_sanitised.index("(")
        depth = 0
        body_chunks: list[str] = []

        for offset, ch in enumerate(first_sanitised[open_index:], start=open_index):
            if ch == "(":
                depth += 1
                if depth == 1:
                    continue
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    body_chunks.append(first[open_index + 1 : offset])
                    return "\n".join(body_chunks), 1
            if depth >= 1:
                pass

        body_chunks.append(first[open_index + 1 :])
        index = start + 1
        while index < len(lines):
            line = lines[index]
            sanitised = self._strip_strings_and_comments(line)
            close_offset: int | None = None
            for offset, ch in enumerate(sanitised):
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                    if depth == 0:
                        close_offset = offset
                        break
            if close_offset is not None:
                body_chunks.append(line[:close_offset])
                return "\n".join(body_chunks), index - start + 1
            body_chunks.append(line)
            index += 1
        return "\n".join(body_chunks), index - start

    def _find_unguarded_brace(
        self, raw_line: str, sanitised: str
    ) -> int | None:
        """Return the index of the first ``{`` in *sanitised* (or ``None``).

        The sanitised string has identical length to *raw_line* with strings
        and comments replaced by spaces, so the index is valid in either.
        """
        position = sanitised.find("{")
        if position == -1:
            return None
        return position

    def _strip_strings_and_comments(self, line: str) -> str:
        """Replace string literals and inline comments with spaces.

        Preserves length so that indices computed against the result remain
        valid in the original line.
        """
        result: list[str] = []
        i = 0
        length = len(line)
        while i < length:
            ch = line[i]
            if ch == "/" and i + 1 < length and line[i + 1] == "/":
                result.append(" " * (length - i))
                break
            if ch == "/" and i + 1 < length and line[i + 1] == "*":
                end = line.find("*/", i + 2)
                if end == -1:
                    result.append(" " * (length - i))
                    break
                result.append(" " * (end + 2 - i))
                i = end + 2
                continue
            if ch in ('"', "'", "`"):
                quote = ch
                start = i
                i += 1
                while i < length:
                    if line[i] == "\\" and quote != "`" and i + 1 < length:
                        i += 2
                        continue
                    if line[i] == quote:
                        i += 1
                        break
                    i += 1
                result.append(" " * (i - start))
                continue
            result.append(ch)
            i += 1
        return "".join(result)

    def _parse_group(self, kind: str, body: str) -> list[GoDeclaration]:
        """Parse the inside of a ``type|const|var (...)`` block."""
        declarations: list[GoDeclaration] = []
        pending_doc: list[str] = []
        lines = body.splitlines()

        for raw in lines:
            stripped = raw.strip()
            if not stripped:
                pending_doc = []
                continue
            if stripped.startswith("//"):
                pending_doc.extend(self._consume_line_comment_block(stripped))
                continue
            decl = self._build_declaration(
                kind=kind,
                signature=stripped,
                doc="\n".join(pending_doc).strip(),
            )
            if decl is not None:
                declarations.append(decl)
            pending_doc = []
        return declarations

    def _build_declaration(
        self, kind: str, signature: str, doc: str
    ) -> GoDeclaration | None:
        """Construct a ``GoDeclaration`` from raw signature text.

        Returns ``None`` if the declaration is unexported, anonymous, or the
        signature could not be parsed.
        """
        signature = signature.strip().rstrip(",;")
        if not signature:
            return None

        if kind == "func":
            head = signature
            if head.startswith("func"):
                head = head[len("func") :].lstrip()
            match = re.match(
                r"(?:\((?P<recv>[^)]*)\)\s+)?(?P<name>\w+)", head
            )
            if not match:
                return None
            name = match.group("name")
            receiver = match.group("recv")
            if not name or not name[0].isupper():
                return None
            return GoDeclaration(
                kind="func",
                name=name,
                signature=self._normalise_signature("func " + head),
                doc=doc,
                receiver=receiver.strip() if receiver else None,
            )

        head = signature
        if head.startswith(kind):
            head = head[len(kind) :].lstrip()
        if not head:
            return None
        match = re.match(r"(?P<name>\w+)", head)
        if not match:
            return None
        name = match.group("name")
        if not name or not name[0].isupper():
            return None
        return GoDeclaration(
            kind=kind,
            name=name,
            signature=self._normalise_signature(f"{kind} {head}"),
            doc=doc,
        )

    def _normalise_signature(self, signature: str) -> str:
        """Collapse whitespace runs in a signature for stable rendering."""
        return re.sub(r"\s+", " ", signature).strip()

    def _sort_declarations(
        self, declarations: list[GoDeclaration]
    ) -> list[GoDeclaration]:
        """Order declarations to match ``go doc`` output: const, var, type, func."""
        order = {"const": 0, "var": 1, "type": 2, "func": 3}
        return sorted(
            declarations,
            key=lambda d: (order.get(d.kind, 99), d.name),
        )

    def render_markdown(self, package: GoPackage) -> str:
        """Render a ``GoPackage`` as a markdown document for indexing."""
        sections: list[str] = []
        sections.append(f"# Package {package.name}")
        sections.append(f"`import \"{package.import_path}\"`")
        if package.doc:
            sections.append(package.doc)

        if package.declarations:
            sections.append("## Index")
            index_lines: list[str] = []
            for decl in package.declarations:
                if decl.kind == "func" and decl.receiver:
                    index_lines.append(
                        f"- method `({decl.receiver}) {decl.name}`"
                    )
                else:
                    index_lines.append(f"- {decl.kind} `{decl.name}`")
            sections.append("\n".join(index_lines))

        for decl in package.declarations:
            heading = self._declaration_heading(decl)
            block = [heading, f"```go\n{decl.signature}\n```"]
            if decl.doc:
                block.append(decl.doc)
            sections.append("\n\n".join(block))

        return "\n\n".join(sections).strip() + "\n"

    def _declaration_heading(self, decl: GoDeclaration) -> str:
        """Produce a heading for a declaration block."""
        if decl.kind == "func" and decl.receiver:
            return f"### method ({decl.receiver}) {decl.name}"
        return f"### {decl.kind} {decl.name}"

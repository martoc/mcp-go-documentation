"""Parser for Go documentation markdown and HTML files."""

import json
import re
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]

from mcp_go_documentation.models import Document, DocumentMetadata


class DocumentParser:
    """Parses Go website documentation files.

    Handles two formats found in the ``golang/website`` ``_content`` tree:

    * Markdown files (``.md``) with YAML frontmatter delimited by ``---``.
    * HTML files (``.html``) with JSON metadata embedded in a leading
      ``<!--{ ... }-->`` comment block.
    """

    GO_DOCS_BASE_URL = "https://go.dev"

    HTML_METADATA_RE = re.compile(r"^\s*<!--\s*(\{.*?\})\s*-->", re.DOTALL)

    def parse_file(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse a documentation file and extract metadata and content.

        Args:
            file_path: Path to the documentation file (markdown or HTML).
            base_path: Base path of the documentation directory
                (the ``_content`` directory).

        Returns:
            Document instance or None if parsing fails or the suffix is
            unsupported.
        """
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".md":
                return self._parse_markdown(file_path, base_path)
            if suffix == ".html":
                return self._parse_html(file_path, base_path)
            return None
        except Exception:
            return None

    def _parse_markdown(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse a markdown file with YAML frontmatter.

        Args:
            file_path: Path to the markdown file.
            base_path: Base path of the documentation directory.

        Returns:
            Document instance or None if parsing fails.
        """
        post = frontmatter.load(file_path)
        metadata = self._extract_markdown_metadata(post.metadata, file_path)
        relative_path = file_path.relative_to(base_path)
        section = self._extract_section(relative_path)
        url = self._compute_url(relative_path)
        content = self._clean_markdown_content(post.content)

        return Document(
            path=str(relative_path),
            title=metadata.title,
            description=metadata.description,
            section=section,
            content=content,
            url=url,
        )

    def _parse_html(self, file_path: Path, base_path: Path) -> Document | None:
        """Parse an HTML file with optional JSON metadata header.

        Args:
            file_path: Path to the HTML file.
            base_path: Base path of the documentation directory.

        Returns:
            Document instance or None if parsing fails.
        """
        raw = file_path.read_text(encoding="utf-8")
        metadata_dict, body = self._extract_html_metadata_block(raw)
        metadata = self._build_metadata_from_html(metadata_dict, file_path)
        relative_path = file_path.relative_to(base_path)
        section = self._extract_section(relative_path)
        url = self._compute_url(relative_path)
        content = self._clean_html_content(body)

        return Document(
            path=str(relative_path),
            title=metadata.title,
            description=metadata.description,
            section=section,
            content=content,
            url=url,
        )

    def _extract_html_metadata_block(self, raw: str) -> tuple[dict[str, object], str]:
        """Extract the leading ``<!--{ ... }-->`` JSON metadata block.

        Args:
            raw: Raw HTML file contents.

        Returns:
            Tuple of metadata dictionary (empty if absent or invalid) and the
            body with the metadata block removed.
        """
        match = self.HTML_METADATA_RE.match(raw)
        if not match:
            return {}, raw

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            return {}, raw[match.end() :]

        if not isinstance(data, dict):
            return {}, raw[match.end() :]

        return data, raw[match.end() :]

    def _extract_markdown_metadata(
        self, metadata: dict[str, object], file_path: Path
    ) -> DocumentMetadata:
        """Extract structured metadata from markdown frontmatter.

        Args:
            metadata: Dictionary of frontmatter fields.
            file_path: Path to the file for fallback title extraction.

        Returns:
            DocumentMetadata instance.
        """
        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            title = self._fallback_title(file_path)

        description = metadata.get("summary")
        if not isinstance(description, str):
            description = None

        return DocumentMetadata(title=title, description=description)

    def _build_metadata_from_html(
        self, metadata: dict[str, object], file_path: Path
    ) -> DocumentMetadata:
        """Build metadata from an HTML metadata dictionary.

        Args:
            metadata: Parsed JSON metadata from the HTML comment block.
            file_path: Path to the file for fallback title extraction.

        Returns:
            DocumentMetadata instance.
        """
        title = metadata.get("Title") or metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            title = self._fallback_title(file_path)

        return DocumentMetadata(title=title, description=None)

    def _fallback_title(self, file_path: Path) -> str:
        """Derive a human-readable title from the filename.

        Args:
            file_path: Path to the documentation file.

        Returns:
            Title string derived from the filename stem.
        """
        return file_path.stem.replace("-", " ").replace("_", " ").title()

    def _extract_section(self, relative_path: Path) -> str:
        """Extract the top-level section from the path.

        Args:
            relative_path: Path relative to the ``_content`` directory.

        Returns:
            Section name (first directory component or 'root' if the file is
            directly inside ``_content``).
        """
        parts = relative_path.parts
        return parts[0] if len(parts) > 1 else "root"

    def _compute_url(self, relative_path: Path) -> str:
        """Compute the go.dev documentation URL.

        Args:
            relative_path: Path relative to the ``_content`` directory.

        Returns:
            Full URL to the documentation page.
        """
        path_str = str(relative_path)
        # Drop the file extension.
        path_str = re.sub(r"\.(md|html)$", "", path_str)
        # Treat ``index`` pages as their parent directory.
        path_str = re.sub(r"(^|/)index$", r"\1", path_str)
        # Strip a trailing slash if we collapsed an ``index`` away.
        path_str = path_str.rstrip("/")

        if path_str:
            return f"{self.GO_DOCS_BASE_URL}/{path_str}"
        return f"{self.GO_DOCS_BASE_URL}/"

    def _clean_markdown_content(self, content: str) -> str:
        """Strip raw HTML markup from markdown content for indexing.

        Args:
            content: Raw markdown content with the frontmatter removed.

        Returns:
            Cleaned content suitable for full-text indexing.
        """
        # Remove HTML comments.
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        # Remove HTML tags whilst preserving the surrounding text.
        content = re.sub(r"<[^>]+>", "", content)
        return content.strip()

    def _clean_html_content(self, content: str) -> str:
        """Strip script, style and tag noise from HTML for indexing.

        Args:
            content: HTML body with the metadata block removed.

        Returns:
            Cleaned plain-text content suitable for full-text indexing.
        """
        # Drop ``<script>`` and ``<style>`` blocks (with their content).
        content = re.sub(r"<script\b[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r"<style\b[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
        # Drop HTML comments.
        content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
        # Drop remaining HTML tags whilst preserving inner text.
        content = re.sub(r"<[^>]+>", " ", content)
        # Collapse whitespace runs.
        content = re.sub(r"\s+", " ", content)
        return content.strip()

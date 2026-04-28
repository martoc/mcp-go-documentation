"""Indexer for Go documentation from the golang/website repository."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.go_source_parser import (
    GoPackage,
    GoSourceParser,
)
from mcp_go_documentation.models import Document
from mcp_go_documentation.parser import DocumentParser

logger = logging.getLogger(__name__)


class GoDocsIndexer:
    """Indexes Go documentation from the golang/website GitHub repository."""

    GOLANG_REPO = "https://github.com/golang/website.git"
    SPARSE_CHECKOUT_PATHS: ClassVar[list[str]] = ["_content"]
    CONTENT_PATH = "_content"
    SUPPORTED_SUFFIXES: ClassVar[tuple[str, ...]] = (".md", ".html")
    EXCLUDED_DIRECTORIES: ClassVar[frozenset[str]] = frozenset({
        "assets",
        "css",
        "fonts",
        "images",
        "js",
    })

    def __init__(self, database: DocumentDatabase) -> None:
        """Initialise indexer with database instance.

        Args:
            database: DocumentDatabase instance for storing documents.
        """
        self.database = database
        self.parser = DocumentParser()

    def index_from_git(self, branch: str = "master", shallow: bool = True) -> int:
        """Clone golang/website and index documentation.

        Args:
            branch: Git branch to clone.
            shallow: Whether to do a shallow clone with sparse checkout.

        Returns:
            Number of documents indexed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "website"
            self._clone_repository(repo_path, branch, shallow)
            return self._index_directory(repo_path)

    def index_from_path(self, docs_path: Path) -> int:
        """Index documentation from a local repository checkout.

        Args:
            docs_path: Path to the repository root directory (one level above
                ``_content``).

        Returns:
            Number of documents indexed.
        """
        return self._index_directory(docs_path)

    def _clone_repository(self, target_path: Path, branch: str, shallow: bool) -> None:
        """Clone the golang/website repository.

        Args:
            target_path: Directory to clone into.
            branch: Git branch to clone.
            shallow: Whether to do a shallow clone with sparse checkout.
        """
        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1", "--filter=blob:none", "--sparse"])
        cmd.extend(["--branch", branch, self.GOLANG_REPO, str(target_path)])

        logger.info("Cloning golang/website repository...")
        subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603

        if shallow:
            logger.info("Setting up sparse checkout for documentation directories...")
            subprocess.run(  # noqa: S603
                ["git", "-C", str(target_path), "sparse-checkout", "set", *self.SPARSE_CHECKOUT_PATHS],  # noqa: S607
                check=True,
                capture_output=True,
            )

        logger.info("Repository cloned successfully")

    def _index_directory(self, repo_path: Path) -> int:
        """Index all documentation files in the repository.

        Args:
            repo_path: Path to the repository root.

        Returns:
            Number of documents indexed.

        Raises:
            ValueError: If the content path does not exist.
        """
        content_path = repo_path / self.CONTENT_PATH
        if not content_path.exists():
            msg = f"Content path does not exist: {content_path}"
            raise ValueError(msg)

        files = self._collect_files(content_path)
        logger.info("Found %d documentation files to index", len(files))

        indexed_count = 0
        for file_path in files:
            document = self.parser.parse_file(file_path, content_path)
            if document is None:
                logger.warning("Failed to parse: %s", file_path)
                continue
            self.database.upsert_document(document)
            indexed_count += 1
            logger.debug("Indexed: %s", document.path)

        logger.info("Successfully indexed %d documents", indexed_count)
        return indexed_count

    def _collect_files(self, content_path: Path) -> list[Path]:
        """Collect all supported files under the content directory.

        Args:
            content_path: Path to the ``_content`` directory.

        Returns:
            Sorted list of paths to supported documentation files, excluding
            asset directories.
        """
        files: list[Path] = []
        for suffix in self.SUPPORTED_SUFFIXES:
            for candidate in content_path.rglob(f"*{suffix}"):
                if not candidate.is_file():
                    continue
                relative_parts = candidate.relative_to(content_path).parts
                if relative_parts and relative_parts[0] in self.EXCLUDED_DIRECTORIES:
                    continue
                files.append(candidate)
        files.sort()
        return files

    def rebuild_index(self, branch: str = "master") -> int:
        """Clear the existing index and rebuild from scratch.

        Args:
            branch: Git branch to index from.

        Returns:
            Number of documents indexed.
        """
        logger.info("Clearing existing index...")
        self.database.clear()
        return self.index_from_git(branch)


class GoStdlibIndexer:
    """Indexes Go standard library documentation from ``golang/go`` source."""

    GOLANG_GO_REPO = "https://github.com/golang/go.git"
    SPARSE_CHECKOUT_PATHS: ClassVar[list[str]] = ["src"]
    SOURCE_PATH = "src"
    SECTION = "std"
    PKG_GO_DEV_BASE_URL = "https://pkg.go.dev"

    EXCLUDED_TOP_LEVEL: ClassVar[frozenset[str]] = frozenset({
        "cmd",
        "vendor",
    })
    EXCLUDED_DIR_NAMES: ClassVar[frozenset[str]] = frozenset({
        "testdata",
    })

    def __init__(self, database: DocumentDatabase) -> None:
        """Initialise the stdlib indexer.

        Args:
            database: ``DocumentDatabase`` used to upsert package documents.
        """
        self.database = database
        self.parser = GoSourceParser()

    def index_from_git(
        self, ref: str = "master", shallow: bool = True
    ) -> int:
        """Clone ``golang/go`` and index the standard library.

        Args:
            ref: Git ref (branch or tag, for example ``go1.26.2``).
            shallow: Whether to do a shallow clone with sparse checkout.

        Returns:
            Number of packages indexed.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "go"
            self._clone_repository(repo_path, ref, shallow)
            return self.index_from_path(repo_path)

    def index_from_path(self, repo_path: Path) -> int:
        """Index the standard library from a local ``golang/go`` checkout.

        Args:
            repo_path: Path to the repository root (containing ``src/``).

        Returns:
            Number of packages indexed.

        Raises:
            ValueError: If the ``src`` directory cannot be found.
        """
        source_path = repo_path / self.SOURCE_PATH
        if not source_path.exists():
            msg = f"Source path does not exist: {source_path}"
            raise ValueError(msg)

        package_dirs = self._collect_package_directories(source_path)
        logger.info("Found %d standard library packages to index", len(package_dirs))

        indexed = 0
        for package_dir in package_dirs:
            import_path = str(package_dir.relative_to(source_path)).replace("\\", "/")
            package = self.parser.parse_package(package_dir, import_path)
            if package is None:
                logger.debug("Skipping non-package directory: %s", import_path)
                continue
            document = self._build_document(package)
            self.database.upsert_document(document)
            indexed += 1
            logger.debug("Indexed stdlib package: %s", import_path)

        logger.info("Successfully indexed %d standard library packages", indexed)
        return indexed

    def _clone_repository(
        self, target_path: Path, ref: str, shallow: bool
    ) -> None:
        """Clone the ``golang/go`` repository at the requested ref."""
        cmd = ["git", "clone"]
        if shallow:
            cmd.extend(["--depth", "1", "--filter=blob:none", "--sparse"])
        cmd.extend(["--branch", ref, self.GOLANG_GO_REPO, str(target_path)])

        logger.info("Cloning golang/go repository at %s...", ref)
        subprocess.run(cmd, check=True, capture_output=True)  # noqa: S603

        if shallow:
            logger.info("Setting up sparse checkout for src/...")
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "-C",
                    str(target_path),
                    "sparse-checkout",
                    "set",
                    *self.SPARSE_CHECKOUT_PATHS,
                ],
                check=True,
                capture_output=True,
            )
        logger.info("Repository cloned successfully")

    def _collect_package_directories(self, source_path: Path) -> list[Path]:
        """Find every directory under ``src/`` that constitutes a Go package.

        A directory qualifies when it contains at least one non-test ``*.go``
        file.  Directories under ``cmd/``, ``vendor/`` or any ``testdata``
        subtree are skipped to align with the public ``pkg.go.dev/std`` view.
        """
        results: list[Path] = []
        for candidate in sorted(source_path.rglob("*.go")):
            if not candidate.is_file():
                continue
            if candidate.name.endswith("_test.go"):
                continue
            relative_parts = candidate.relative_to(source_path).parts
            if not relative_parts:
                continue
            if relative_parts[0] in self.EXCLUDED_TOP_LEVEL:
                continue
            if any(part in self.EXCLUDED_DIR_NAMES for part in relative_parts[:-1]):
                continue
            package_dir = candidate.parent
            if package_dir not in results:
                results.append(package_dir)
        return results

    def _build_document(self, package: GoPackage) -> Document:
        """Convert a parsed Go package into a database ``Document``."""
        title = f"{package.name} - {package.import_path}"
        description = self._extract_summary(package.doc)
        url = f"{self.PKG_GO_DEV_BASE_URL}/{package.import_path}"
        path = f"{self.SECTION}/{package.import_path}"
        content = self.parser.render_markdown(package)

        return Document(
            path=path,
            title=title,
            description=description,
            section=self.SECTION,
            content=content,
            url=url,
        )

    def _extract_summary(self, doc: str) -> str | None:
        """Extract the first sentence/paragraph of the package doc as a summary."""
        if not doc:
            return None
        first_paragraph = doc.split("\n\n", 1)[0]
        first_paragraph = " ".join(first_paragraph.split())
        if not first_paragraph:
            return None
        if len(first_paragraph) > 280:
            return first_paragraph[:277].rstrip() + "..."
        return first_paragraph

    def rebuild_index(self, ref: str = "master") -> int:
        """Clear stdlib documents and rebuild from scratch.

        Args:
            ref: Git ref to index from.

        Returns:
            Number of packages indexed.
        """
        logger.info("Clearing existing stdlib index entries...")
        self.database.clear_section(self.SECTION)
        return self.index_from_git(ref)

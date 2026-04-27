"""Indexer for Go documentation from the golang/website repository."""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import ClassVar

from mcp_go_documentation.database import DocumentDatabase
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

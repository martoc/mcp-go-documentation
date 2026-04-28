"""Command-line interface for the Go documentation indexer."""

import argparse
import logging
import sys
from pathlib import Path

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.indexer import GoDocsIndexer, GoStdlibIndexer
from mcp_go_documentation.server import DEFAULT_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

VALID_SOURCES = ("website", "stdlib", "all")


def cmd_index(args: argparse.Namespace) -> int:
    """Index Go documentation.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    db_path = Path(args.database) if args.database else DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Using database: %s", db_path)

    database = DocumentDatabase(db_path)

    if args.rebuild:
        logger.info("Clearing existing index...")
        database.clear()

    total_indexed = 0

    if args.source in ("website", "all"):
        website_indexer = GoDocsIndexer(database)
        website_count = website_indexer.index_from_git(branch=args.website_branch)
        logger.info("Website pages indexed: %d", website_count)
        total_indexed += website_count

    if args.source in ("stdlib", "all"):
        stdlib_indexer = GoStdlibIndexer(database)
        stdlib_count = stdlib_indexer.index_from_git(ref=args.stdlib_ref)
        logger.info("Standard library packages indexed: %d", stdlib_count)
        total_indexed += stdlib_count

    logger.info("Indexed %d documents in total", total_indexed)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show index statistics.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    db_path = Path(args.database) if args.database else DEFAULT_DB_PATH

    if not db_path.exists():
        logger.error("Database not found: %s", db_path)
        logger.info("Run 'go-docs-index index' to create the index")
        return 1

    database = DocumentDatabase(db_path)
    count = database.get_document_count()
    logger.info("Total indexed documents: %d", count)
    return 0


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="go-docs-index",
        description="Go documentation indexer for the MCP server",
    )
    parser.add_argument(
        "--database",
        "-d",
        help="Path to SQLite database file",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser("index", help="Index Go documentation")
    index_parser.add_argument(
        "--source",
        "-s",
        choices=VALID_SOURCES,
        default="all",
        help=(
            "Which source to index: 'website' (golang/website _content), "
            "'stdlib' (golang/go src/) or 'all' (default)."
        ),
    )
    index_parser.add_argument(
        "--website-branch",
        default="master",
        help="Git branch of golang/website to index (default: master).",
    )
    index_parser.add_argument(
        "--stdlib-ref",
        default="master",
        help=(
            "Git ref of golang/go to index — branch (master) or release tag "
            "such as 'go1.26.2' (default: master)."
        ),
    )
    index_parser.add_argument(
        "--rebuild",
        "-r",
        action="store_true",
        help="Clear the existing index before indexing.",
    )
    index_parser.set_defaults(func=cmd_index)

    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

"""Command-line interface for the Go documentation indexer."""

import argparse
import logging
import sys
from pathlib import Path

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.indexer import GoDocsIndexer
from mcp_go_documentation.server import DEFAULT_DB_PATH

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


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
    indexer = GoDocsIndexer(database)

    if args.rebuild:
        count = indexer.rebuild_index(branch=args.branch)
    else:
        count = indexer.index_from_git(branch=args.branch)

    logger.info("Indexed %d documents", count)
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
        "--branch",
        "-b",
        default="master",
        help="Git branch to index (default: master)",
    )
    index_parser.add_argument(
        "--rebuild",
        "-r",
        action="store_true",
        help="Clear the existing index before indexing",
    )
    index_parser.set_defaults(func=cmd_index)

    stats_parser = subparsers.add_parser("stats", help="Show index statistics")
    stats_parser.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    result: int = args.func(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

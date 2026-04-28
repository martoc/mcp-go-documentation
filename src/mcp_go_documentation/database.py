"""SQLite FTS5 database operations for Go documentation."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from mcp_go_documentation.models import Document, SearchResult


class DocumentDatabase:
    """Manages the SQLite FTS5 database for documentation search."""

    def __init__(self, db_path: Path) -> None:
        """Initialise database with the given path.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._initialise_schema()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections.

        Yields:
            SQLite connection with Row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _initialise_schema(self) -> None:
        """Create database schema if it doesn't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    section TEXT,
                    url TEXT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    description,
                    content,
                    content='documents',
                    content_rowid='id',
                    tokenize='porter unicode61'
                );

                CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                    INSERT INTO documents_fts(rowid, title, description, content)
                    VALUES (new.id, new.title, new.description, new.content);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
                    VALUES ('delete', old.id, old.title, old.description, old.content);
                END;

                CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                    INSERT INTO documents_fts(documents_fts, rowid, title, description, content)
                    VALUES ('delete', old.id, old.title, old.description, old.content);
                    INSERT INTO documents_fts(rowid, title, description, content)
                    VALUES (new.id, new.title, new.description, new.content);
                END;

                CREATE INDEX IF NOT EXISTS idx_documents_section ON documents(section);
            """)
            conn.commit()

    def upsert_document(self, doc: Document) -> None:
        """Insert or update a document.

        Args:
            doc: Document to insert or update.
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (path, title, description, section, url, content)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    title = excluded.title,
                    description = excluded.description,
                    section = excluded.section,
                    url = excluded.url,
                    content = excluded.content,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (doc.path, doc.title, doc.description, doc.section, doc.url, doc.content),
            )
            conn.commit()

    def search(self, query: str, section: str | None = None, limit: int = 10) -> list[SearchResult]:
        """Search documents using FTS5.

        Args:
            query: Search query string.
            section: Optional section filter.
            limit: Maximum number of results.

        Returns:
            List of SearchResult instances ordered by relevance.
        """
        with self._get_connection() as conn:
            sql = """
                SELECT
                    d.path,
                    d.title,
                    d.url,
                    d.section,
                    snippet(documents_fts, 2, '<mark>', '</mark>', '...', 64) as snippet,
                    bm25(documents_fts, 5.0, 2.0, 1.0) as score
                FROM documents_fts
                JOIN documents d ON documents_fts.rowid = d.id
                WHERE documents_fts MATCH ?
            """
            params: list[str | int] = [query]

            if section:
                sql += " AND d.section = ?"
                params.append(section)

            sql += " ORDER BY score LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append(
                    SearchResult(
                        path=row["path"],
                        title=row["title"],
                        url=row["url"],
                        section=row["section"],
                        snippet=row["snippet"],
                        score=abs(row["score"]),
                    )
                )
            return results

    def get_document(self, path: str) -> Document | None:
        """Retrieve a document by path.

        Args:
            path: Relative path to the document.

        Returns:
            Document instance or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM documents WHERE path = ?",
                (path,),
            )
            row = cursor.fetchone()
            if row:
                return Document(
                    path=row["path"],
                    title=row["title"],
                    description=row["description"],
                    section=row["section"],
                    content=row["content"],
                    url=row["url"],
                )
            return None

    def clear(self) -> None:
        """Clear all documents from the database."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents")
            conn.commit()

    def clear_section(self, section: str) -> None:
        """Clear all documents within a single section.

        Args:
            section: Section name to remove.
        """
        with self._get_connection() as conn:
            conn.execute("DELETE FROM documents WHERE section = ?", (section,))
            conn.commit()

    def get_document_count(self) -> int:
        """Return the total number of indexed documents.

        Returns:
            Count of documents in the database.
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            result = cursor.fetchone()
            return int(result[0]) if result else 0

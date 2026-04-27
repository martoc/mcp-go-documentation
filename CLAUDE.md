# Claude Code Instructions

This file contains instructions for Claude Code when working with the MCP Go Documentation Server codebase.

## Project Overview

This is an MCP (Model Context Protocol) server that provides search and retrieval tools for Go (Golang) documentation. It uses:
- FastMCP for the MCP server framework
- SQLite FTS5 for full-text search with BM25 ranking
- Python-frontmatter for parsing markdown files with YAML frontmatter
- A bespoke regex-based extractor for HTML files with the `<!--{ ... }-->` JSON metadata block used by `golang/website`
- Sparse Git checkout for efficient cloning of the `_content` documentation directory

## Code Principles

### British English
- Use British English in all code, comments, and documentation
- Examples: "initialise" not "initialize", "colour" not "color"

### Type Safety
- All functions must have type hints
- Use modern union syntax: `str | None` instead of `Optional[str]`
- Run mypy in strict mode before committing

### Error Handling
- Use explicit error handling
- Raise appropriate exceptions with descriptive messages
- Never silently fail

### Code Style
- Follow PEP 8 guidelines
- Maximum line length: 120 characters
- Use ruff for linting and formatting
- See CODESTYLE.md for detailed style guidelines

## Development Workflow

### Making Changes

1. **Before starting**:
   - Ensure the development environment is initialised: `make init`
   - Understand the existing code structure

2. **During development**:
   - Write tests for new functionality
   - Update type hints as needed
   - Add docstrings following Google style

3. **Before committing**:
   - Format code: `make format`
   - Run linter: `make lint`
   - Run type checker: `make typecheck`
   - Run tests: `make test`
   - Or run all checks: `make build`

### Testing

- Write tests using pytest
- Place tests in `tests/` directory
- Mirror source structure in test files
- Test both success and failure cases
- Aim for high coverage (>80%)

## Project Structure

```
mcp-go-documentation/
├── src/mcp_go_documentation/
│   ├── __init__.py         # Package initialisation
│   ├── models.py           # Data models (Document, SearchResult, etc.)
│   ├── database.py         # SQLite FTS5 database operations
│   ├── parser.py           # Markdown and HTML file parser
│   ├── indexer.py          # Documentation indexer
│   ├── server.py           # FastMCP server implementation
│   └── cli.py              # Command-line interface
├── tests/                  # Test files
├── data/                   # SQLite database storage
├── pyproject.toml          # Project configuration
├── Makefile                # Build automation
├── Dockerfile              # Container configuration
└── README.md               # Project documentation
```

## MCP Tools

The server exposes two MCP tools:

1. **search_documentation**: Full-text search with optional section filtering
2. **read_documentation**: Retrieve the complete content of a document

Both tools return JSON-formatted responses.

## Database Schema

The database has two main tables:
- `documents`: Main document storage
- `documents_fts`: FTS5 virtual table for search

Triggers keep the FTS index synchronised with the main table.

## Common Patterns

### Database Operations
Always use the context manager pattern:
```python
with self._get_connection() as conn:
    # Perform operations
    conn.commit()
```

### Lazy Initialisation
The server uses lazy initialisation for the database:
```python
_database: DocumentDatabase | None = None

def get_database() -> DocumentDatabase:
    global _database
    if _database is None:
        _database = DocumentDatabase(db_path)
    return _database
```

### Error Messages
Provide helpful error messages with suggestions:
```python
return json.dumps({
    "error": f"Document not found: {path}",
    "suggestion": "Use search_documentation to find valid document paths.",
})
```

## Debugging

### Index Issues
If the index isn't working correctly:
1. Check index statistics: `uv run go-docs-index stats`
2. Rebuild the index: `uv run go-docs-index index --rebuild`
3. Check database file permissions
4. Verify the Git clone succeeded

### Search Not Finding Results
1. Verify the Porter stemmer is being applied
2. Check BM25 scoring weights
3. Examine the FTS5 query syntax
4. Test with simpler queries

### Docker Build Failures
1. Ensure Git is available in the container
2. Check network connectivity during the build
3. Verify the sparse checkout configuration
4. Check uv installation

## Container Image

The `martoc/mcp-go-documentation` container image is published to Docker Hub with the documentation index pre-built.

- **Image**: `martoc/mcp-go-documentation`
- **Platforms**: `linux/amd64`, `linux/arm64`
- **CI/CD**: Built and published automatically via GitHub Actions on push to `main`
- **Index**: Pre-built at image build time from `golang/website` `master` branch

## Documentation URLs

The Go documentation URL pattern:
```
https://go.dev/{path}
```

The parser strips `.md` and `.html` extensions and collapses `index.md` /
`index.html` files to their parent directory when computing URLs.

## Source Content Layout

The `golang/website` repository keeps all human-readable content under
`_content/`. The indexer walks that tree and indexes:

- `*.md` files with optional YAML frontmatter (handled with `python-frontmatter`)
- `*.html` files with optional JSON metadata in a leading
  `<!--{ ... }-->` comment block (parsed with `json.loads`)

Asset directories such as `_content/css`, `_content/js`, `_content/fonts`,
`_content/images`, and `_content/assets` are skipped.

## Git Operations

The indexer uses sparse checkout to clone only the `_content` directory:
```bash
git clone --depth 1 --filter=blob:none --sparse --branch master ...
git sparse-checkout set _content
```

This significantly reduces clone time and disk usage.

## Performance Considerations

- **SQLite FTS5**: Provides fast full-text search with BM25 ranking
- **Sparse checkout**: Reduces clone size by fetching only the required directory
- **Lazy loading**: Database initialised only when needed
- **Connection pooling**: Not needed for SQLite (file-based)

## Best Practices

1. **Never** commit without running `make build`
2. **Always** write tests for new features
3. **Keep** functions focused and single-purpose
4. **Use** type hints consistently
5. **Document** non-obvious behaviour
6. **Follow** British English spelling
7. **Update** documentation when changing behaviour

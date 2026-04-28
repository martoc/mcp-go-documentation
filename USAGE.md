# Usage Guide

This guide provides detailed instructions for using the MCP Go Documentation Server.

## Installation

### Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) package manager
- Git
- Docker (optional, for containerised deployment)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/martoc/mcp-go-documentation.git
   cd mcp-go-documentation
   ```

2. Initialise the development environment:
   ```bash
   make init
   ```

3. Build the documentation index:
   ```bash
   make index
   ```

## Indexing Documentation

The indexer maintains a single SQLite database that combines two sources:

- the [`golang/website`](https://github.com/golang/website) `_content/` directory (markdown and HTML pages such as Effective Go, the FAQ, blog posts, the Tour); and
- the [`golang/go`](https://github.com/golang/go) `src/` directory — every standard library package extracted from godoc comments and exposed under the `std` section (matching [pkg.go.dev/std](https://pkg.go.dev/std)).

### Initial Indexing

Index everything (both sources):

```bash
uv run go-docs-index index
```

### Rebuilding the Index

Clear the existing index and rebuild from scratch:

```bash
uv run go-docs-index index --rebuild
```

### Indexing a Single Source

```bash
# Only the narrative content from golang/website
uv run go-docs-index index --source website

# Only the standard library packages from golang/go src/
uv run go-docs-index index --source stdlib
```

### Pinning a Git Ref

```bash
# Index the website pages from the master branch
uv run go-docs-index index --source website --website-branch master

# Index the standard library at a specific Go release
uv run go-docs-index index --source stdlib --stdlib-ref go1.26.2
```

### Index Statistics

View the number of indexed documents:

```bash
uv run go-docs-index stats
```

## Running the MCP Server

### Using the Container Image (Recommended)

The `martoc/mcp-go-documentation` container image is published to Docker Hub with the documentation index pre-built. Available for `linux/amd64` and `linux/arm64`.

```bash
# Pull and run the server
docker run -i --rm martoc/mcp-go-documentation:latest
```

### Local Development

Run the server directly using uv:

```bash
make run
# or
uv run mcp-go-documentation
```

### Building a Local Docker Image

Build and run the server in a Docker container:

```bash
make docker-build
make docker-run
```

## MCP Client Configuration

### Claude Code (Container Image)

Add to your project's `.mcp.json` to use the published container image:

```json
{
  "mcpServers": {
    "go-documentation": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "martoc/mcp-go-documentation:latest"]
    }
  }
}
```

### Claude Code (Local Development)

Add to your project's `.mcp.json` for local development:

```json
{
  "mcpServers": {
    "go-documentation": {
      "command": "uv",
      "args": ["run", "mcp-go-documentation"],
      "cwd": "/path/to/mcp-go-documentation"
    }
  }
}
```

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "go-documentation": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "martoc/mcp-go-documentation:latest"]
    }
  }
}
```

## Using the Tools

### Searching Documentation

Search for topics in the Go documentation:

```
Search for "goroutines"
Search for "go modules" in section "ref"
Search for "generics" with limit 20
```

Example response:

```json
{
  "query": "goroutines",
  "section_filter": null,
  "result_count": 5,
  "results": [
    {
      "title": "Effective Go",
      "url": "https://go.dev/doc/effective_go",
      "path": "doc/effective_go.html",
      "section": "doc",
      "snippet": "...goroutines are functions executing concurrently...",
      "relevance_score": 12.5432
    }
  ]
}
```

### Reading Documentation

Retrieve the full content of a specific page:

```
Read documentation at path "doc/effective_go.html"
```

Example response:

```json
{
  "path": "doc/effective_go.html",
  "title": "Effective Go",
  "description": null,
  "section": "doc",
  "url": "https://go.dev/doc/effective_go",
  "content": "Introduction Go is an open-source programming language..."
}
```

## Common Sections

The Go documentation is organised into several sections.  The website
sections are derived from the top-level directories under `_content/` in
`golang/website`; the `std` section comes from `golang/go` `src/`:

- **doc**: Main reference documentation (Effective Go, the FAQ, install guides, tutorials)
- **blog**: Blog posts published on go.dev
- **ref**: Language and module references
- **tour**: A Tour of Go content
- **gopls**: gopls (the Go language server) documentation
- **learn**: Curated learning paths and external resources
- **solutions**: Use-case write-ups
- **talks**: Conference talks
- **wiki**: Community-maintained articles
- **root**: Top-level pages such as `about.md`, `help.md`, `index.md`
- **std**: Standard library packages (one document per package; paths look like `std/fmt`, `std/net/http`, `std/encoding/json`)

Use these section names with the `section` parameter to filter search results.

### Reading a Standard Library Package

```text
Read documentation at path "std/net/http"
```

The returned content is rendered from godoc comments in the package's `.go`
files: a package-level summary followed by an index of exported declarations
and per-declaration signatures with their doc comments.

## Development Workflow

### Code Quality Checks

Run all code quality checks:

```bash
make build
```

This runs:
- Linter (ruff)
- Type checker (mypy)
- Tests with coverage (pytest)

### Individual Checks

```bash
make lint       # Run linter only
make typecheck  # Run type checker only
make test       # Run tests only
make format     # Format code
```

### Updating Dependencies

Update the lock file:

```bash
make generate
```

## Troubleshooting

### Index Build Fails

If the index build fails, try:

1. Check your internet connection
2. Verify Git is installed and accessible
3. Try rebuilding with explicit refs:
   ```bash
   uv run go-docs-index index --rebuild \
       --website-branch master --stdlib-ref master
   ```
4. If only the standard library clone is failing, you can isolate it:
   ```bash
   uv run go-docs-index index --source stdlib --stdlib-ref go1.26.2
   ```

### No Search Results

If searches return no results:

1. Verify the index is built:
   ```bash
   uv run go-docs-index stats
   ```

2. Rebuild the index if necessary:
   ```bash
   uv run go-docs-index index --rebuild
   ```

### Database Location

The default database location is `data/go_docs.db`. To use a custom location:

```bash
uv run go-docs-index index --database /path/to/custom.db
```

## Performance Considerations

- **Initial indexing**: May take a few minutes depending on network speed; cloning
  `golang/go` is the dominant cost (sparse checkout limits this to `src/`)
- **Sparse checkout**: Only `_content/` from `golang/website` and `src/` from
  `golang/go` are cloned, reducing download size considerably
- **Search performance**: FTS5 with BM25 ranking provides fast, relevant results
- **Memory usage**: Minimal during operation; database is SQLite-based

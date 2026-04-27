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

### Initial Indexing

Index the Go documentation from the master branch:

```bash
uv run go-docs-index index
```

### Rebuilding the Index

Clear the existing index and rebuild from scratch:

```bash
uv run go-docs-index index --rebuild
```

### Indexing a Specific Branch

Index documentation from a specific Git branch:

```bash
uv run go-docs-index index --branch master
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

The Go documentation is organised into several sections, derived from the
top-level directories under `_content/` in `golang/website`:

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

Use these section names with the `section` parameter to filter search results.

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
3. Try rebuilding with a different branch:
   ```bash
   uv run go-docs-index index --rebuild --branch master
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

- **Initial indexing**: May take a few minutes depending on network speed
- **Sparse checkout**: Only the `_content/` directory is cloned, reducing download size
- **Search performance**: FTS5 with BM25 ranking provides fast, relevant results
- **Memory usage**: Minimal during operation; database is SQLite-based

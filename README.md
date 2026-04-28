[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-green.svg)](https://modelcontextprotocol.io/)

# MCP Go Documentation Server

An MCP (Model Context Protocol) server that provides search and retrieval tools for [Go (Golang)](https://go.dev) documentation. This server enables AI assistants like Claude to search and read the official Go documentation directly, including:

- the language specification, Effective Go, the modules reference, blog posts, tour material and the rest of the narrative content published from [`golang/website`](https://github.com/golang/website); and
- the **standard library package documentation** ([pkg.go.dev/std](https://pkg.go.dev/std)) extracted from godoc comments in [`golang/go`](https://github.com/golang/go) `src/` — covering every package such as `fmt`, `net/http`, `encoding/json`, `context`, `errors`, and so on.

## Features

- **Full-text search** using SQLite FTS5 with BM25 ranking and Porter stemming
- **Section filtering** to narrow search results by documentation category (`doc`, `blog`, `ref`, `tour`, `gopls`, `std`, etc.)
- **Markdown and HTML support** for the mixed content under `_content/`
- **Standard library indexing** by extracting godoc-style comments from `golang/go` `src/` Go source files
- **Sparse checkout** for efficient cloning of only the relevant directories
- **Docker support** with both indices baked into the image at build time
- **STDIO transport** for seamless MCP client integration

## Quick Start

### Using the Container Image (Recommended)

The `martoc/mcp-go-documentation` container image is published to Docker Hub with the documentation index pre-built. Available for `linux/amd64` and `linux/arm64`.

```bash
# Pull and run the server
docker run -i --rm martoc/mcp-go-documentation:latest
```

### Building Locally with Docker

```bash
# Build the Docker image (includes the pre-indexed documentation)
make docker-build

# Test the server
make docker-run
```

### Using uv (Local Development)

```bash
# Initialise the environment
make init

# Build the documentation index
make index

# Run the server
make run
```

## Container Image

The `martoc/mcp-go-documentation` container image is published to [Docker Hub](https://hub.docker.com/r/martoc/mcp-go-documentation). It includes the pre-built documentation index so the server is ready to use immediately.

| Property | Value |
|----------|-------|
| Registry | Docker Hub |
| Image | `martoc/mcp-go-documentation` |
| Platforms | `linux/amd64`, `linux/arm64` |
| Base image | `python:3.12-slim` |
| Index | Pre-built at image build time from `golang/website` `master` and `golang/go` `master` (`src/` only, sparse checkout) |

```bash
# Pull the latest image
docker pull martoc/mcp-go-documentation:latest

# Run the MCP server
docker run -i --rm martoc/mcp-go-documentation:latest
```

## Configuration

### Claude Code / Claude Desktop

Add to your `.mcp.json` or global settings to use the published container image:

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

For a locally built Docker image:

```json
{
  "mcpServers": {
    "go-documentation": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "mcp-go-documentation"]
    }
  }
}
```

For local development without Docker:

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

## MCP Tools

| Tool | Description |
|------|-------------|
| `search_documentation` | Search Go documentation by keyword query with optional section filtering |
| `read_documentation` | Retrieve the full content of a specific documentation page |

### search_documentation

Search Go documentation using full-text search with stemming support.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | Yes | - | Search terms (supports stemming) |
| `section` | string | No | None | Filter by section (e.g., doc, blog, ref) |
| `limit` | integer | No | 10 | Maximum results (1-50) |

**Common Sections:** `doc`, `blog`, `ref`, `tour`, `gopls`, `talks`, `wiki`, `solutions`, `learn`, `std`

The `std` section contains one document per standard library package (for example `std/fmt`, `std/net/http`, `std/encoding/json`).

### read_documentation

Retrieve the full content of a documentation page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Relative path to the document (from search results) |

## CLI Commands

```bash
# Build/rebuild the full index (golang/website + standard library)
uv run go-docs-index index
uv run go-docs-index index --rebuild

# Limit which source is indexed
uv run go-docs-index index --source website
uv run go-docs-index index --source stdlib

# Pin a specific Go release tag for the standard library
uv run go-docs-index index --source stdlib --stdlib-ref go1.26.2

# Show index statistics
uv run go-docs-index stats
```

## Development

```bash
make init       # Initialise development environment
make build      # Run full build (lint, typecheck, test)
make test       # Run tests with coverage
make format     # Format code
make lint       # Run linter
make typecheck  # Run type checker
```

## Documentation

- [USAGE.md](USAGE.md) - Detailed usage instructions
- [CODESTYLE.md](CODESTYLE.md) - Code style guidelines
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions

## Licence

This project is licensed under the MIT Licence - see the [LICENSE](LICENSE) file for details.

FROM python:3.12-slim

WORKDIR /app

# Install git for cloning the golang/website and golang/go repositories at
# build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files.
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/

# Install dependencies.
RUN uv sync --no-dev

# Bake both the golang/website narrative pages and the golang/go standard
# library package documentation into the index at build time.
RUN uv run go-docs-index index --source all

# Run the MCP server.
CMD ["uv", "run", "mcp-go-documentation"]

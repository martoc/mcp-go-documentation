FROM python:3.12-slim

WORKDIR /app

# Disable FastMCP's startup update check; the container has no need to
# reach PyPI at runtime.
ENV FASTMCP_CHECK_FOR_UPDATES=off

# Install git for cloning the golang/website and golang/go repositories at
# build time.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files.
COPY pyproject.toml uv.lock README.md ./
COPY src/ src/
COPY data/ data/

# Install dependencies from the committed lockfile, baking them into the
# image at build time.
RUN uv sync --locked --no-dev

# Bake both the golang/website narrative pages and the golang/go standard
# library package documentation into the index at build time.
RUN uv run --no-sync go-docs-index index --source all

# Run the MCP server directly from the baked venv so no dependency
# resolution happens on container start.
CMD ["/app/.venv/bin/mcp-go-documentation"]

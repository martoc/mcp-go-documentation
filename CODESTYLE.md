# Code Style Guide

This document outlines the code style and quality standards for the MCP Go Documentation Server.

## Language

- Use **British English** throughout the codebase
- This applies to:
  - Code comments
  - Documentation strings
  - Variable names
  - Error messages
  - Documentation files

## Python Style

### PEP 8 Compliance

All Python code must follow [PEP 8](https://peps.python.org/pep-0008/) guidelines.

### Type Hints

- Use type hints for all function and method signatures
- Use `from __future__ import annotations` for forward references where needed
- Use modern union syntax: `str | None` instead of `Optional[str]`
- Use `collections.abc` for generic types: `list[str]`, `dict[str, int]`

Example:
```python
def search_documents(
    query: str,
    section: str | None = None,
    limit: int = 10,
) -> list[SearchResult]:
    """Search documents with optional filtering."""
    ...
```

### Imports

- Organise imports in three groups:
  1. Standard library imports
  2. Third-party library imports
  3. Local application imports
- Sort imports alphabetically within each group
- Place all imports at the top of the file
- Do not import inside functions or methods

Example:
```python
import logging
import sqlite3
from pathlib import Path

from fastmcp import FastMCP

from mcp_go_documentation.database import DocumentDatabase
from mcp_go_documentation.models import Document
```

### Docstrings

- Use Google-style docstrings for all public modules, classes, and functions
- Include type information in docstrings for parameters and return values
- Provide clear descriptions and examples where appropriate

### Code Organisation

- Maximum line length: 120 characters
- Use 4 spaces for indentation (no tabs)
- Use blank lines to separate logical sections
- Keep functions focused and single-purpose
- Prefer composition over inheritance

### Error Handling

- Use explicit error handling over silent failures
- Raise appropriate exceptions with descriptive messages
- Use context managers for resource management
- Log errors appropriately with the logging module

### Naming Conventions

- Classes: `PascalCase` (e.g., `DocumentDatabase`)
- Functions/methods: `snake_case` (e.g., `search_documents`)
- Constants: `UPPER_CASE` (e.g., `DEFAULT_DB_PATH`)
- Private members: prefix with `_` (e.g., `_get_connection`)

### Design Patterns

Use design patterns where appropriate:
- **Context Manager**: For database connections
- **Factory Pattern**: For creating database instances
- **Singleton Pattern**: For lazy initialisation of shared resources

## Testing

### Test Framework

- Use pytest for all tests
- Organise tests in the `tests/` directory
- Mirror the source structure in test files

### Test Coverage

- Aim for high test coverage (>80%)
- Test both success and failure cases
- Test edge cases and boundary conditions
- Use parametrised tests for multiple scenarios

### Test Style

- Test files: `test_*.py`
- Test functions: `test_*`
- Use descriptive test names
- Use fixtures for common setup

## Code Quality Tools

### Ruff

- Linter and formatter
- Configuration in `pyproject.toml`
- Run: `make lint` or `make format`

### Mypy

- Static type checker
- Strict mode enabled
- Configuration in `pyproject.toml`
- Run: `make typecheck`

### Pytest

- Testing framework
- Coverage reporting enabled
- Configuration in `pyproject.toml`
- Run: `make test`

## Git Workflow

### Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/)
- Use imperative mood in commit messages
- Keep commits focused and atomic
- Do not add co-authors in commit messages

### Branches

- Branch naming: `feature/xyz`, `bugfix/xyz`, `hotfix/xyz`
- Create pull requests for all changes
- Never push directly to `main`

### Pull Requests

- Provide a clear description of changes
- Reference related issues
- Ensure all tests pass

## Documentation

### Markdown Files

- Use British English
- Keep lines under 120 characters where practical
- Use code blocks with language specification
- Include a table of contents for long documents

### Comments

- Write clear, concise comments
- Explain "why", not "what"
- Update comments when code changes
- Remove outdated comments

## Pre-commit Checks

Before committing, ensure:
1. Code is formatted: `make format`
2. Linter passes: `make lint`
3. Type checker passes: `make typecheck`
4. Tests pass: `make test`
5. Or run all: `make build`

## Dependencies

- Minimise external dependencies
- Pin versions in `pyproject.toml`
- Update lock file: `make generate`
- Document dependency rationale

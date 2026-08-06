"""Tests for the server entrypoint."""

from unittest.mock import patch

import pytest

from mcp_go_documentation.server import run_server


def test_run_server_defaults_to_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that stdio transport is used when MCP_TRANSPORT is unset."""
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)

    with patch("mcp_go_documentation.server.mcp.run") as mock_run:
        run_server()

    mock_run.assert_called_once_with(transport="stdio")


def test_run_server_http_uses_custom_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that MCP_HOST/MCP_PORT are passed through when set alongside MCP_TRANSPORT=http."""
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "9000")

    with patch("mcp_go_documentation.server.mcp.run") as mock_run:
        run_server()

    mock_run.assert_called_once_with(transport="http", host="127.0.0.1", port=9000)


def test_run_server_http_defaults_host_and_port(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that HTTP transport falls back to 0.0.0.0:8000 when MCP_HOST/MCP_PORT are unset."""
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.delenv("MCP_HOST", raising=False)
    monkeypatch.delenv("MCP_PORT", raising=False)

    with patch("mcp_go_documentation.server.mcp.run") as mock_run:
        run_server()

    mock_run.assert_called_once_with(transport="http", host="0.0.0.0", port=8000)  # noqa: S104

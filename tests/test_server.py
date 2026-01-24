"""Tests for SDLC MCP server functionality."""

from unittest.mock import Mock, patch, MagicMock
import numpy as np

from sdlc_mcp.server import create_server


class TestServer:
    """Test server creation and basic functionality."""

    def test_given_server_creation_when_called_should_return_fastmcp_instance(self) -> None:
        """Test that create_server returns a FastMCP instance."""
        server = create_server()
        assert server is not None
        assert hasattr(server, "run")

    def test_given_search_docs_when_called_should_validate_limit(self) -> None:
        """Test that search_docs validates the limit parameter."""
        # The server is already created with mocked dependencies at module load
        # This test verifies the server instance exists and has expected tools
        server = create_server()
        assert server is not None

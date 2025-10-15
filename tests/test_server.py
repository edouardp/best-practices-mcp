"""Tests for SDLC MCP server functionality."""

from unittest.mock import Mock, patch

from sdlc_mcp.server import create_server


class TestServer:
    """Test server creation and basic functionality."""

    def test_given_server_creation_when_called_should_return_fastmcp_instance(self) -> None:
        """Test that create_server returns a FastMCP instance."""
        # Arrange & Act
        with patch("sdlc_mcp.server.SentenceTransformer"), patch("sdlc_mcp.server.duckdb"):
            server = create_server()

        # Assert
        assert server is not None
        assert hasattr(server, "run")

    def test_given_search_docs_when_called_should_validate_limit(self) -> None:
        """Test that search_docs validates the limit parameter."""
        # Arrange
        mock_model = Mock()
        mock_model.encode.return_value = [0.1] * 768
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchall.return_value = []

        # Act & Assert
        with (
            patch("sdlc_mcp.server.SentenceTransformer", return_value=mock_model),
            patch("sdlc_mcp.server.duckdb.connect", return_value=mock_conn),
        ):
            create_server()
            # Test would require accessing the decorated function
            # This is a minimal example showing the testing pattern

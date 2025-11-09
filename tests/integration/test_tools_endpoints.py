"""Integration tests for tools endpoints"""
import pytest


@pytest.mark.integration
class TestListToolsEndpoint:
    """Test /tools/list endpoint"""

    def test_list_tools_returns_200(self, test_client):
        """Test that list tools endpoint returns 200"""
        response = test_client.post("/tools/list")
        assert response.status_code == 200

    def test_list_tools_returns_tools_array(self, test_client):
        """Test that list tools returns an array of tools"""
        response = test_client.post("/tools/list")
        data = response.json()

        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0

    def test_list_tools_includes_required_fields(self, test_client):
        """Test that each tool has required fields"""
        response = test_client.post("/tools/list")
        data = response.json()

        for tool in data["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_list_tools_includes_all_operations(self, test_client):
        """Test that all operations are listed"""
        response = test_client.post("/tools/list")
        data = response.json()

        tool_names = [tool["name"] for tool in data["tools"]]

        # Check for read operations
        assert "search" in tool_names
        assert "read" in tool_names
        assert "search_read" in tool_names
        assert "search_count" in tool_names
        assert "fields_get" in tool_names
        assert "default_get" in tool_names

        # Check for write operations
        assert "create" in tool_names
        assert "write" in tool_names

        # Check for delete operations
        assert "unlink" in tool_names


@pytest.mark.integration
class TestCallToolEndpoint:
    """Test /tools/call endpoint"""

    def test_call_tool_missing_api_key(self, test_client):
        """Test tool call without API key"""
        payload = {
            "name": "search",
            "arguments": {}
        }

        response = test_client.post("/tools/call", json=payload)

        # Should return 200 with error response (not 403)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["status"] == "auth_failed"

    def test_call_tool_invalid_api_key(self, test_client):
        """Test tool call with invalid API key"""
        payload = {
            "name": "search",
            "arguments": {}
        }

        response = test_client.post(
            "/tools/call",
            json=payload,
            headers={"X-API-Key": "invalid_key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["status"] == "auth_failed"

    @pytest.mark.skip(reason="Requires full app lifespan with connection_manager initialization")
    def test_call_tool_missing_tool_name(self, test_client, test_api_key):
        """Test tool call without tool name"""
        payload = {
            "arguments": {}
        }

        response = test_client.post(
            "/tools/call",
            json=payload,
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["status"] == "invalid_request"

    @pytest.mark.skip(reason="Requires full app lifespan with connection_manager initialization")
    def test_call_tool_unknown_tool(self, test_client, test_api_key):
        """Test tool call with unknown tool"""
        payload = {
            "name": "unknown_tool",
            "arguments": {}
        }

        response = test_client.post(
            "/tools/call",
            json=payload,
            headers={"X-API-Key": test_api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "tool_not_found" in data["status"]

    def test_call_tool_requires_valid_api_key_format(self, test_client):
        """Test that valid API key format is required"""
        payload = {
            "name": "search",
            "arguments": {
                "model": "res.partner"
            }
        }

        # Invalid key format should be rejected
        response = test_client.post(
            "/tools/call",
            json=payload,
            headers={"X-API-Key": "not-a-valid-fernet-key"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "auth_failed"

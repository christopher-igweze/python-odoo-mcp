"""Unit tests for MCP tools with mocked OdooClient"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.odoo.client import OdooClient, OdooClientError
from src.tools.tools import (
    create,
    default_get,
    fields_get,
    read,
    search_count,
    search_read,
    search,
    unlink,
    write,
)


@pytest.mark.unit
class TestReadTools:
    """Test read operation tools"""

    @pytest.fixture
    def mock_client(self):
        """Create mock OdooClient"""
        client = Mock(spec=OdooClient)
        return client

    async def test_search_success(self, mock_client):
        """Test search function returns results"""
        # Arrange
        mock_client.search = AsyncMock(return_value=[1, 2, 3])

        # Act
        result = await search(
            client=mock_client,
            model="res.partner",
            domain=[("name", "=", "Test")],
            limit=10,
        )

        # Assert
        assert "ids" in result
        assert result["ids"] == [1, 2, 3]
        assert result["count"] == 3
        mock_client.search.assert_called_once()

    async def test_search_empty_result(self, mock_client):
        """Test search function with no results"""
        # Arrange
        mock_client.search = AsyncMock(return_value=[])

        # Act
        result = await search(client=mock_client, model="res.partner")

        # Assert
        assert "ids" in result
        assert result["ids"] == []
        assert result["count"] == 0

    async def test_read_success(self, mock_client):
        """Test read function returns records"""
        # Arrange
        mock_client.read = AsyncMock(
            return_value=[{"id": 1, "name": "Test"}]
        )

        # Act
        result = await read(
            client=mock_client, model="res.partner", ids=[1]
        )

        # Assert
        assert "records" in result
        assert len(result["records"]) == 1
        assert result["count"] == 1
        mock_client.read.assert_called_once()

    async def test_search_read_success(self, mock_client):
        """Test search_read function"""
        # Arrange
        mock_client.search_read = AsyncMock(
            return_value=[{"id": 1, "name": "Test"}]
        )

        # Act
        result = await search_read(
            client=mock_client, model="res.partner"
        )

        # Assert
        assert "records" in result
        assert result["count"] == 1

    async def test_search_count_success(self, mock_client):
        """Test search_count function returns count"""
        # Arrange
        mock_client.search_count = AsyncMock(return_value=42)

        # Act
        result = await search_count(
            client=mock_client, model="res.partner"
        )

        # Assert
        assert "count" in result
        assert result["count"] == 42
        mock_client.search_count.assert_called_once()

    async def test_fields_get_success(self, mock_client):
        """Test fields_get function returns schema"""
        # Arrange
        mock_client.fields_get = AsyncMock(
            return_value={"id": {"string": "ID"}, "name": {"string": "Name"}}
        )

        # Act
        result = await fields_get(client=mock_client, model="res.partner")

        # Assert
        assert "fields" in result
        assert result["count"] == 2

    async def test_default_get_success(self, mock_client):
        """Test default_get function returns defaults"""
        # Arrange
        mock_client.default_get = AsyncMock(return_value={"name": ""})

        # Act
        result = await default_get(
            client=mock_client, model="res.partner"
        )

        # Assert
        assert "defaults" in result


@pytest.mark.unit
class TestWriteTools:
    """Test write operation tools"""

    @pytest.fixture
    def mock_client(self):
        """Create mock OdooClient"""
        client = Mock(spec=OdooClient)
        return client

    async def test_create_success(self, mock_client):
        """Test create function returns new ID"""
        # Arrange
        mock_client.create = AsyncMock(return_value=99)

        # Act
        result = await create(
            client=mock_client,
            model="res.partner",
            values={"name": "New Partner"},
        )

        # Assert
        assert "id" in result
        assert result["id"] == 99
        assert result["status"] == "created"
        mock_client.create.assert_called_once()

    async def test_write_success(self, mock_client):
        """Test write function updates records"""
        # Arrange
        mock_client.write = AsyncMock(return_value=True)

        # Act
        result = await write(
            client=mock_client,
            model="res.partner",
            ids=[1, 2],
            values={"name": "Updated"},
        )

        # Assert
        assert result["success"] is True
        assert result["count"] == 2
        assert result["status"] == "updated"
        mock_client.write.assert_called_once()


@pytest.mark.unit
class TestDeleteTools:
    """Test delete operation tools"""

    @pytest.fixture
    def mock_client(self):
        """Create mock OdooClient"""
        client = Mock(spec=OdooClient)
        return client

    async def test_unlink_success(self, mock_client):
        """Test unlink function deletes records"""
        # Arrange
        mock_client.unlink = AsyncMock(return_value=True)

        # Act
        result = await unlink(
            client=mock_client, model="res.partner", ids=[1, 2]
        )

        # Assert
        assert result["success"] is True
        assert result["count"] == 2
        assert result["status"] == "deleted"
        mock_client.unlink.assert_called_once()


@pytest.mark.unit
class TestToolErrorHandling:
    """Test error handling in tools"""

    @pytest.fixture
    def mock_client(self):
        """Create mock OdooClient"""
        client = Mock(spec=OdooClient)
        return client

    async def test_search_handles_odoo_client_error(self, mock_client):
        """Test search handles OdooClientError gracefully"""
        # Arrange
        mock_client.search = AsyncMock(
            side_effect=OdooClientError("Permission denied")
        )

        # Act
        result = await search(client=mock_client, model="res.partner")

        # Assert
        assert "error" in result
        assert "Permission denied" in result["error"]

    async def test_read_handles_permission_error(self, mock_client):
        """Test read handles PermissionError"""
        # Arrange
        mock_client.read = AsyncMock(
            side_effect=PermissionError("Read not allowed")
        )

        # Act
        result = await read(
            client=mock_client, model="res.partner", ids=[1]
        )

        # Assert
        assert "error" in result
        assert "Read not allowed" in result["error"]

    async def test_create_handles_odoo_client_error(self, mock_client):
        """Test create handles OdooClientError"""
        # Arrange
        mock_client.create = AsyncMock(
            side_effect=OdooClientError("Creation failed")
        )

        # Act
        result = await create(
            client=mock_client, model="res.partner", values={"name": "Test"}
        )

        # Assert
        assert "error" in result
        assert "Creation failed" in result["error"]

    async def test_write_handles_permission_error(self, mock_client):
        """Test write handles PermissionError"""
        # Arrange
        mock_client.write = AsyncMock(
            side_effect=PermissionError("Write not allowed")
        )

        # Act
        result = await write(
            client=mock_client, model="res.partner", ids=[1], values={"name": "Updated"}
        )

        # Assert
        assert "error" in result
        assert "Write not allowed" in result["error"]

    async def test_unlink_handles_odoo_client_error(self, mock_client):
        """Test unlink handles OdooClientError"""
        # Arrange
        mock_client.unlink = AsyncMock(
            side_effect=OdooClientError("Deletion failed")
        )

        # Act
        result = await unlink(client=mock_client, model="res.partner", ids=[1])

        # Assert
        assert "error" in result
        assert "Deletion failed" in result["error"]

    async def test_fields_get_handles_error(self, mock_client):
        """Test fields_get handles errors"""
        # Arrange
        mock_client.fields_get = AsyncMock(
            side_effect=OdooClientError("Schema fetch failed")
        )

        # Act
        result = await fields_get(client=mock_client, model="res.partner")

        # Assert
        assert "error" in result
        assert "Schema fetch failed" in result["error"]

    async def test_search_read_handles_error(self, mock_client):
        """Test search_read handles errors"""
        # Arrange
        mock_client.search_read = AsyncMock(
            side_effect=PermissionError("Search failed")
        )

        # Act
        result = await search_read(client=mock_client, model="res.partner")

        # Assert
        assert "error" in result
        assert "Search failed" in result["error"]

    async def test_search_count_handles_error(self, mock_client):
        """Test search_count handles errors"""
        # Arrange
        mock_client.search_count = AsyncMock(
            side_effect=OdooClientError("Count failed")
        )

        # Act
        result = await search_count(client=mock_client, model="res.partner")

        # Assert
        assert "error" in result
        assert "Count failed" in result["error"]

    async def test_default_get_handles_error(self, mock_client):
        """Test default_get handles errors"""
        # Arrange
        mock_client.default_get = AsyncMock(
            side_effect=PermissionError("Default get failed")
        )

        # Act
        result = await default_get(client=mock_client, model="res.partner")

        # Assert
        assert "error" in result
        assert "Default get failed" in result["error"]

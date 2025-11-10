"""Unit tests for OdooClient with mocked XML-RPC connections"""

from unittest.mock import AsyncMock, Mock
from xmlrpc.client import Fault

import pytest

from src.auth.scope_validator import ScopeValidator
from src.connection.manager import OdooConnectionManager
from src.odoo.client import OdooClient, OdooClientError


@pytest.mark.unit
class TestOdooClientReadOperations:
    """Test OdooClient read operations (search, read, search_read, etc.)"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager"""
        manager = Mock(spec=OdooConnectionManager)
        models_proxy = Mock()
        manager.get_connection.return_value = (1, "test_db", models_proxy)
        return manager

    @pytest.fixture
    def mock_scope_validator(self):
        """Create mock scope validator that allows all operations"""
        validator = Mock(spec=ScopeValidator)
        validator.scope_string = "res.partner:RWD,sale.order:RW,*:R"
        validator.enforce_call = Mock()  # Allows all by default
        return validator

    @pytest.fixture
    def odoo_client(self, mock_connection_manager, mock_scope_validator):
        """Create OdooClient instance with mocks"""
        return OdooClient(
            odoo_url="https://demo.odoo.com",
            odoo_db="demo_db",
            username="test_user",
            password="test_pass",
            connection_manager=mock_connection_manager,
            scope_validator=mock_scope_validator,
        )

    async def test_search_returns_record_ids(
        self, odoo_client, mock_connection_manager
    ):
        """Test search returns list of record IDs"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = [1, 2, 3]

        # Act
        result = await odoo_client.search(
            "res.partner", [("name", "=", "Test")], limit=10
        )

        # Assert
        assert result == [1, 2, 3]
        models_proxy.execute_kw.assert_called_once()

    async def test_search_with_empty_domain(
        self, odoo_client, mock_connection_manager
    ):
        """Test search with empty domain"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = [10, 20]

        # Act
        result = await odoo_client.search("res.partner")

        # Assert
        assert result == [10, 20]

    async def test_search_returns_empty_list(self, odoo_client, mock_connection_manager):
        """Test search returns empty list when no records match"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = []

        # Act
        result = await odoo_client.search("res.partner", [("id", "=", 999)])

        # Assert
        assert result == []

    async def test_read_returns_records(self, odoo_client, mock_connection_manager):
        """Test read returns record data"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        expected_records = [{"id": 1, "name": "Test Partner"}]
        models_proxy.execute_kw.return_value = expected_records

        # Act
        result = await odoo_client.read("res.partner", [1])

        # Assert
        assert result == expected_records

    async def test_read_with_specific_fields(
        self, odoo_client, mock_connection_manager
    ):
        """Test read with specific field list"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        expected_records = [{"id": 1, "name": "Test"}]
        models_proxy.execute_kw.return_value = expected_records

        # Act
        result = await odoo_client.read("res.partner", [1], ["id", "name"])

        # Assert
        assert result == expected_records
        models_proxy.execute_kw.assert_called_once()

    async def test_search_read_returns_combined_result(
        self, odoo_client, mock_connection_manager
    ):
        """Test search_read returns both IDs and data"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        expected_data = [{"id": 1, "name": "Test"}]
        models_proxy.execute_kw.return_value = expected_data

        # Act
        result = await odoo_client.search_read("res.partner", [("name", "=", "Test")])

        # Assert
        assert result == expected_data

    async def test_search_count_returns_integer(
        self, odoo_client, mock_connection_manager
    ):
        """Test search_count returns record count"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = 42

        # Act
        result = await odoo_client.search_count("res.partner")

        # Assert
        assert result == 42

    async def test_fields_get_returns_field_schema(
        self, odoo_client, mock_connection_manager
    ):
        """Test fields_get returns model schema"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        schema = {"id": {"string": "ID"}, "name": {"string": "Name"}}
        models_proxy.execute_kw.return_value = schema

        # Act
        result = await odoo_client.fields_get("res.partner")

        # Assert
        assert result == schema

    async def test_default_get_returns_defaults(
        self, odoo_client, mock_connection_manager
    ):
        """Test default_get returns default values"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        defaults = {"name": "", "email": ""}
        models_proxy.execute_kw.return_value = defaults

        # Act
        result = await odoo_client.default_get("res.partner", ["name", "email"])

        # Assert
        assert result == defaults


@pytest.mark.unit
class TestOdooClientWriteOperations:
    """Test OdooClient write operations (create, write)"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager"""
        manager = Mock(spec=OdooConnectionManager)
        models_proxy = Mock()
        manager.get_connection.return_value = (1, "test_db", models_proxy)
        return manager

    @pytest.fixture
    def mock_scope_validator(self):
        """Create mock scope validator allowing writes"""
        validator = Mock(spec=ScopeValidator)
        validator.scope_string = "res.partner:RWD"
        validator.enforce_call = Mock()
        return validator

    @pytest.fixture
    def odoo_client(self, mock_connection_manager, mock_scope_validator):
        """Create OdooClient instance"""
        return OdooClient(
            odoo_url="https://demo.odoo.com",
            odoo_db="demo_db",
            username="test_user",
            password="test_pass",
            connection_manager=mock_connection_manager,
            scope_validator=mock_scope_validator,
        )

    async def test_create_returns_record_id(
        self, odoo_client, mock_connection_manager
    ):
        """Test create returns new record ID"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = 99

        # Act
        result = await odoo_client.create("res.partner", {"name": "New Partner"})

        # Assert
        assert result == 99
        models_proxy.execute_kw.assert_called_once()

    async def test_write_updates_records(
        self, odoo_client, mock_connection_manager
    ):
        """Test write updates records"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = True

        # Act
        result = await odoo_client.write("res.partner", [1, 2], {"name": "Updated"})

        # Assert
        assert result is True
        models_proxy.execute_kw.assert_called_once()


@pytest.mark.unit
class TestOdooClientDeleteOperations:
    """Test OdooClient delete operations (unlink)"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager"""
        manager = Mock(spec=OdooConnectionManager)
        models_proxy = Mock()
        manager.get_connection.return_value = (1, "test_db", models_proxy)
        return manager

    @pytest.fixture
    def mock_scope_validator(self):
        """Create mock scope validator allowing deletes"""
        validator = Mock(spec=ScopeValidator)
        validator.scope_string = "res.partner:RWD"
        validator.enforce_call = Mock()
        return validator

    @pytest.fixture
    def odoo_client(self, mock_connection_manager, mock_scope_validator):
        """Create OdooClient instance"""
        return OdooClient(
            odoo_url="https://demo.odoo.com",
            odoo_db="demo_db",
            username="test_user",
            password="test_pass",
            connection_manager=mock_connection_manager,
            scope_validator=mock_scope_validator,
        )

    async def test_unlink_deletes_records(
        self, odoo_client, mock_connection_manager
    ):
        """Test unlink deletes records"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.return_value = True

        # Act
        result = await odoo_client.unlink("res.partner", [1, 2, 3])

        # Assert
        assert result is True


@pytest.mark.unit
class TestOdooClientErrorHandling:
    """Test OdooClient error handling"""

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager"""
        manager = Mock(spec=OdooConnectionManager)
        models_proxy = Mock()
        manager.get_connection.return_value = (1, "test_db", models_proxy)
        return manager

    @pytest.fixture
    def mock_scope_validator(self):
        """Create mock scope validator"""
        validator = Mock(spec=ScopeValidator)
        validator.scope_string = "res.partner:R"  # Read-only
        validator.enforce_call = Mock()
        return validator

    @pytest.fixture
    def odoo_client(self, mock_connection_manager, mock_scope_validator):
        """Create OdooClient instance"""
        return OdooClient(
            odoo_url="https://demo.odoo.com",
            odoo_db="demo_db",
            username="test_user",
            password="test_pass",
            connection_manager=mock_connection_manager,
            scope_validator=mock_scope_validator,
        )

    async def test_scope_enforcement_checked_before_operation(self, odoo_client):
        """Test scope validator is called before operation"""
        # Act
        try:
            await odoo_client.search("res.partner")
        except Exception:
            pass

        # Assert
        odoo_client.scope_validator.enforce_call.assert_called()

    async def test_odoo_fault_raises_client_error(
        self, odoo_client, mock_connection_manager
    ):
        """Test Odoo XML-RPC faults raise OdooClientError"""
        # Arrange
        manager = mock_connection_manager
        models_proxy = manager.get_connection.return_value[2]
        models_proxy.execute_kw.side_effect = Fault(
            1, "Invalid field or access denied"
        )

        # Act & Assert
        with pytest.raises(OdooClientError):
            await odoo_client.search("res.partner")

    async def test_connection_error_propagates(
        self, odoo_client, mock_connection_manager
    ):
        """Test connection errors are propagated"""
        # Arrange
        manager = mock_connection_manager
        manager.get_connection.side_effect = ConnectionError("Cannot connect to Odoo")

        # Act & Assert - ConnectionError is propagated from connection_manager
        with pytest.raises(ConnectionError):
            await odoo_client.search("res.partner")

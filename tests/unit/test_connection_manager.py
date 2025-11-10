"""Unit tests for OdooConnectionManager"""

from unittest.mock import Mock, patch

import pytest

from src.connection.manager import OdooConnectionError, OdooConnectionManager
from src.connection.pool import ConnectionPool


@pytest.mark.unit
class TestOdooConnectionManagerInitialization:
    """Test OdooConnectionManager initialization"""

    def test_connection_manager_initializes_with_pool(self):
        """Test manager initializes with a pool"""
        pool = ConnectionPool()
        manager = OdooConnectionManager(pool)
        assert manager.pool == pool

    def test_connection_manager_has_pool_reference(self):
        """Test manager maintains pool reference"""
        pool = ConnectionPool()
        manager = OdooConnectionManager(pool)
        assert manager.pool is pool


@pytest.mark.unit
class TestOdooConnectionManagerPooled:
    """Test connection pooling in manager"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def manager(self, pool):
        """Create a manager with test pool"""
        return OdooConnectionManager(pool)

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_get_connection_checks_pool_first(self, mock_server_proxy, manager):
        """Test manager checks pool before creating new connection"""
        # Pre-populate pool with a connection
        url = "https://example.odoo.com"
        username = "testuser"
        scope = "res.partner:RW"

        mock_models = Mock()
        manager.pool.set(url, username, scope, 123, "testdb", mock_models)

        # Get connection should return cached
        uid, db, models = manager.get_connection(url, "testdb", username, "password", scope)

        assert uid == 123
        assert db == "testdb"
        assert models == mock_models
        # ServerProxy should not be called since we got it from cache
        mock_server_proxy.assert_not_called()

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_get_connection_creates_new_on_cache_miss(
        self, mock_server_proxy, manager
    ):
        """Test manager creates new connection on cache miss"""
        # Setup mocks
        mock_common = Mock()
        mock_common.authenticate.return_value = 42
        mock_models = Mock()

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            elif "/object" in url:
                return mock_models
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        # Get connection with empty pool
        uid, db, models = manager.get_connection(
            "https://example.odoo.com", "testdb", "user1", "secret", "res.partner:R"
        )

        assert uid == 42
        assert db == "testdb"
        assert models == mock_models


@pytest.mark.unit
class TestOdooConnectionManagerAuthentication:
    """Test authentication flow"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def manager(self, pool):
        """Create a manager with test pool"""
        return OdooConnectionManager(pool)

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_get_connection_authenticates_with_credentials(
        self, mock_server_proxy, manager
    ):
        """Test manager passes correct credentials to authenticate"""
        mock_common = Mock()
        mock_common.authenticate.return_value = 100
        mock_models = Mock()

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            elif "/object" in url:
                return mock_models
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        manager.get_connection(
            "https://example.odoo.com",
            "proddb",
            "admin",
            "mypassword",
            "sale.order:RW",
        )

        # Verify authenticate was called with correct args
        mock_common.authenticate.assert_called_once_with("proddb", "admin", "mypassword", {})

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_get_connection_stores_in_pool_after_auth(
        self, mock_server_proxy, manager
    ):
        """Test authenticated connection is stored in pool"""
        mock_common = Mock()
        mock_common.authenticate.return_value = 77
        mock_models = Mock()

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            elif "/object" in url:
                return mock_models
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        manager.get_connection(url, "testdb", username, "pwd", scope)

        # Verify it's now in the pool
        cached = manager.pool.get(url, username, scope)
        assert cached is not None
        assert cached["uid"] == 77


@pytest.mark.unit
class TestOdooConnectionManagerErrors:
    """Test error handling"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def manager(self, pool):
        """Create a manager with test pool"""
        return OdooConnectionManager(pool)

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_authentication_failure_raises_connection_error(
        self, mock_server_proxy, manager
    ):
        """Test failed authentication raises OdooConnectionError"""
        mock_common = Mock()
        mock_common.authenticate.return_value = None  # Auth failure

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        with pytest.raises(OdooConnectionError):
            manager.get_connection(
                "https://example.odoo.com",
                "testdb",
                "baduser",
                "badpass",
                "res.partner:R",
            )

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_xmlrpc_fault_raises_connection_error(
        self, mock_server_proxy, manager
    ):
        """Test XML-RPC fault raises OdooConnectionError"""
        from xmlrpc import client as xmlrpc_client

        mock_common = Mock()
        mock_common.authenticate.side_effect = xmlrpc_client.Fault(1, "Server error")

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        with pytest.raises(OdooConnectionError):
            manager.get_connection(
                "https://example.odoo.com",
                "testdb",
                "user",
                "pass",
                "res.partner:R",
            )

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_network_error_raises_connection_error(
        self, mock_server_proxy, manager
    ):
        """Test network errors raise OdooConnectionError"""
        mock_server_proxy.side_effect = ConnectionError("Network unreachable")

        with pytest.raises(OdooConnectionError):
            manager.get_connection(
                "https://example.odoo.com",
                "testdb",
                "user",
                "pass",
                "res.partner:R",
            )


@pytest.mark.unit
class TestOdooConnectionManagerInvalidation:
    """Test connection invalidation"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def manager(self, pool):
        """Create a manager with test pool"""
        return OdooConnectionManager(pool)

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_invalidate_connection_removes_from_pool(
        self, mock_server_proxy, manager
    ):
        """Test invalidate removes connection from pool"""
        # Setup and cache a connection
        mock_common = Mock()
        mock_common.authenticate.return_value = 42
        mock_models = Mock()

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            elif "/object" in url:
                return mock_models
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        # Create and cache a connection
        manager.get_connection(url, "testdb", username, "pwd", scope)
        assert manager.pool.get(url, username, scope) is not None

        # Invalidate it
        manager.invalidate_connection(url, username, scope)

        # Should no longer be in pool
        assert manager.pool.get(url, username, scope) is None


@pytest.mark.unit
class TestOdooConnectionManagerStats:
    """Test connection manager statistics"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def manager(self, pool):
        """Create a manager with test pool"""
        return OdooConnectionManager(pool)

    @patch("src.connection.manager.xmlrpc_client.ServerProxy")
    def test_get_pool_stats_returns_stats(self, mock_server_proxy, manager):
        """Test get_pool_stats returns pool statistics"""
        # Setup and cache a connection
        mock_common = Mock()
        mock_common.authenticate.return_value = 42
        mock_models = Mock()

        def server_proxy_factory(url):
            if "/common" in url:
                return mock_common
            elif "/object" in url:
                return mock_models
            return Mock()

        mock_server_proxy.side_effect = server_proxy_factory

        manager.get_connection(
            "https://example.odoo.com",
            "testdb",
            "user1",
            "pwd",
            "res.partner:RW",
        )

        stats = manager.get_pool_stats()

        assert "total_connections" in stats
        assert "active_connections" in stats
        assert "expired_connections" in stats
        assert stats["total_connections"] == 1

    def test_get_pool_size_returns_size(self, manager):
        """Test get_pool_size returns pool size"""
        assert manager.get_pool_size() == 0

        # Manually add a connection to pool
        mock_models = Mock()
        manager.pool.set("https://a.odoo.com", "user1", "scope1", 1, "db", mock_models)

        assert manager.get_pool_size() == 1

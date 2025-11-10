"""Unit tests for ConnectionPool with scope-aware caching"""

import hashlib
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from src.connection.pool import ConnectionPool


@pytest.mark.unit
class TestConnectionPoolInitialization:
    """Test ConnectionPool initialization"""

    def test_connection_pool_initializes_empty(self):
        """Test pool starts with no connections"""
        pool = ConnectionPool()
        assert pool.size() == 0

    def test_connection_pool_initializes_with_default_ttl(self):
        """Test pool initializes with 60 minute TTL by default"""
        pool = ConnectionPool()
        stats = pool.stats()
        assert stats["ttl_minutes"] == 60

    def test_connection_pool_initializes_with_custom_ttl(self):
        """Test pool initializes with custom TTL"""
        pool = ConnectionPool(ttl_minutes=30)
        stats = pool.stats()
        assert stats["ttl_minutes"] == 30

    def test_connection_pool_creates_thread_safe_lock(self):
        """Test pool has threading lock for safety"""
        pool = ConnectionPool()
        assert pool.lock is not None


@pytest.mark.unit
class TestConnectionPoolKeyGeneration:
    """Test connection pool key generation"""

    def test_key_creation_is_deterministic(self):
        """Test same inputs produce same key"""
        pool = ConnectionPool()
        url = "https://example.odoo.com"
        username = "user123"
        scope = "res.partner:RW"

        key1 = pool._create_key(url, username, scope)
        key2 = pool._create_key(url, username, scope)

        assert key1 == key2

    def test_key_creation_includes_scope_hash(self):
        """Test scope differences produce different keys"""
        pool = ConnectionPool()
        url = "https://example.odoo.com"
        username = "user123"

        key1 = pool._create_key(url, username, "res.partner:R")
        key2 = pool._create_key(url, username, "res.partner:RW")

        assert key1 != key2

    def test_key_creation_includes_username(self):
        """Test username differences produce different keys"""
        pool = ConnectionPool()
        url = "https://example.odoo.com"
        scope = "res.partner:RW"

        key1 = pool._create_key(url, "user1", scope)
        key2 = pool._create_key(url, "user2", scope)

        assert key1 != key2

    def test_key_creation_includes_url(self):
        """Test URL differences produce different keys"""
        pool = ConnectionPool()
        username = "user123"
        scope = "res.partner:RW"

        key1 = pool._create_key("https://instance1.odoo.com", username, scope)
        key2 = pool._create_key("https://instance2.odoo.com", username, scope)

        assert key1 != key2

    def test_key_is_sha256_hash(self):
        """Test key format is valid SHA256 hash"""
        pool = ConnectionPool()
        key = pool._create_key("https://example.odoo.com", "user", "scope")
        # SHA256 hex produces 64 character string
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


@pytest.mark.unit
class TestConnectionPoolStorage:
    """Test connection pool storage operations"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool(ttl_minutes=60)

    @pytest.fixture
    def mock_models_proxy(self):
        """Create a mock models proxy"""
        return Mock()

    def test_set_stores_connection_in_pool(self, pool, mock_models_proxy):
        """Test connection is stored in pool"""
        pool.set(
            odoo_url="https://example.odoo.com",
            username="user1",
            scope="res.partner:RW",
            uid=42,
            db="testdb",
            models_proxy=mock_models_proxy,
        )

        assert pool.size() == 1

    def test_get_retrieves_stored_connection(self, pool, mock_models_proxy):
        """Test stored connection can be retrieved"""
        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        pool.set(url, username, scope, 42, "testdb", mock_models_proxy)
        cached = pool.get(url, username, scope)

        assert cached is not None
        assert cached["uid"] == 42
        assert cached["db"] == "testdb"
        assert cached["models_proxy"] == mock_models_proxy
        assert cached["scope"] == scope

    def test_get_returns_none_for_missing_connection(self, pool):
        """Test get returns None when connection not cached"""
        result = pool.get(
            odoo_url="https://example.odoo.com",
            username="nonexistent",
            scope="res.partner:R",
        )
        assert result is None

    def test_multiple_connections_stored_separately(self, pool, mock_models_proxy):
        """Test multiple connections with different scopes are stored separately"""
        url = "https://example.odoo.com"
        username = "user1"

        # Store with different scopes
        pool.set(url, username, "res.partner:R", 1, "db", mock_models_proxy)
        pool.set(url, username, "res.partner:RW", 2, "db", mock_models_proxy)

        # Retrieve both
        cached_r = pool.get(url, username, "res.partner:R")
        cached_rw = pool.get(url, username, "res.partner:RW")

        assert cached_r["uid"] == 1
        assert cached_rw["uid"] == 2
        assert pool.size() == 2


@pytest.mark.unit
class TestConnectionPoolExpiration:
    """Test connection pool expiration"""

    @pytest.fixture
    def pool(self):
        """Create a pool with short TTL for testing"""
        return ConnectionPool(ttl_minutes=1)

    @pytest.fixture
    def mock_models_proxy(self):
        """Create a mock models proxy"""
        return Mock()

    def test_expired_connection_returns_none(self, pool, mock_models_proxy):
        """Test expired connection is not returned"""
        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        pool.set(url, username, scope, 42, "testdb", mock_models_proxy)

        # Manually expire the connection
        key = pool._create_key(url, username, scope)
        pool.connections[key]["expires_at"] = datetime.now() - timedelta(seconds=1)

        # Should return None because expired
        result = pool.get(url, username, scope)
        assert result is None

    def test_expired_connection_removed_from_pool(self, pool, mock_models_proxy):
        """Test expired connection is removed from pool on retrieval"""
        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        pool.set(url, username, scope, 42, "testdb", mock_models_proxy)
        assert pool.size() == 1

        # Manually expire the connection
        key = pool._create_key(url, username, scope)
        pool.connections[key]["expires_at"] = datetime.now() - timedelta(seconds=1)

        # Try to get it (should fail and remove it)
        pool.get(url, username, scope)

        # Pool should be empty now
        assert pool.size() == 0

    def test_valid_connection_expires_at_ttl(self):
        """Test connection expires_at is set to TTL from now"""
        # Use a new pool with 1 minute TTL (this pool fixture has ttl_minutes=1)
        pool = ConnectionPool(ttl_minutes=1)
        mock_models_proxy = Mock()

        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        before = datetime.now()
        pool.set(url, username, scope, 42, "testdb", mock_models_proxy)
        after = datetime.now()

        key = pool._create_key(url, username, scope)
        expires_at = pool.connections[key]["expires_at"]

        # Should expire approximately 1 minute from now
        ttl_seconds = 60
        min_expiry = before + timedelta(seconds=ttl_seconds)
        max_expiry = after + timedelta(seconds=ttl_seconds) + timedelta(seconds=1)

        assert min_expiry <= expires_at <= max_expiry


@pytest.mark.unit
class TestConnectionPoolInvalidation:
    """Test connection pool invalidation"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def mock_models_proxy(self):
        """Create a mock models proxy"""
        return Mock()

    def test_invalidate_removes_connection(self, pool, mock_models_proxy):
        """Test invalidate removes connection from pool"""
        url = "https://example.odoo.com"
        username = "user1"
        scope = "res.partner:RW"

        pool.set(url, username, scope, 42, "testdb", mock_models_proxy)
        assert pool.size() == 1

        pool.invalidate(url, username, scope)

        assert pool.size() == 0
        assert pool.get(url, username, scope) is None

    def test_invalidate_with_nonexistent_connection_succeeds(self, pool):
        """Test invalidate silently succeeds for non-existent connections"""
        # Should not raise an error
        pool.invalidate(
            "https://example.odoo.com",
            "nonexistent",
            "res.partner:R",
        )

    def test_invalidate_only_affects_specific_connection(
        self, pool, mock_models_proxy
    ):
        """Test invalidate only removes specified connection"""
        url = "https://example.odoo.com"
        user1_scope = "res.partner:R"
        user2_scope = "res.partner:RW"

        pool.set(url, "user1", user1_scope, 1, "db", mock_models_proxy)
        pool.set(url, "user2", user2_scope, 2, "db", mock_models_proxy)

        pool.invalidate(url, "user1", user1_scope)

        assert pool.size() == 1
        assert pool.get(url, "user2", user2_scope) is not None


@pytest.mark.unit
class TestConnectionPoolStatistics:
    """Test connection pool statistics"""

    @pytest.fixture
    def pool(self):
        """Create a test pool"""
        return ConnectionPool()

    @pytest.fixture
    def mock_models_proxy(self):
        """Create a mock models proxy"""
        return Mock()

    def test_stats_returns_correct_total_connections(self, pool, mock_models_proxy):
        """Test stats returns total connections"""
        pool.set("https://a.odoo.com", "user1", "scope1", 1, "db", mock_models_proxy)
        pool.set("https://b.odoo.com", "user2", "scope2", 2, "db", mock_models_proxy)

        stats = pool.stats()
        assert stats["total_connections"] == 2

    def test_stats_counts_expired_connections(self, pool, mock_models_proxy):
        """Test stats counts expired vs active connections"""
        pool.set("https://a.odoo.com", "user1", "scope1", 1, "db", mock_models_proxy)
        pool.set("https://b.odoo.com", "user2", "scope2", 2, "db", mock_models_proxy)

        # Expire one connection
        all_keys = list(pool.connections.keys())
        pool.connections[all_keys[0]]["expires_at"] = datetime.now() - timedelta(
            seconds=1
        )

        stats = pool.stats()
        assert stats["total_connections"] == 2
        assert stats["expired_connections"] == 1
        assert stats["active_connections"] == 1

    def test_stats_returns_ttl_in_minutes(self, pool):
        """Test stats returns TTL in minutes"""
        stats = pool.stats()
        assert stats["ttl_minutes"] == 60

    def test_size_returns_pool_size(self, pool, mock_models_proxy):
        """Test size method returns number of connections"""
        assert pool.size() == 0

        pool.set("https://a.odoo.com", "user1", "scope1", 1, "db", mock_models_proxy)
        assert pool.size() == 1

        pool.set("https://b.odoo.com", "user2", "scope2", 2, "db", mock_models_proxy)
        assert pool.size() == 2

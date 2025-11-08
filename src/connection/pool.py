"""Connection pooling with scope-aware caching"""
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from xmlrpc import client as xmlrpc_client

logger = logging.getLogger(__name__)

class ConnectionPool:
    """
    Thread-safe connection pool with scope-aware caching.

    Pool key is created from: url + username + scope_hash
    This ensures connections for different scopes are kept separate.
    """

    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize connection pool.

        Args:
            ttl_minutes: Time-to-live for cached connections in minutes
        """
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.max_age = timedelta(minutes=ttl_minutes)
        self.lock = threading.RLock()
        logger.debug(f"ConnectionPool initialized with TTL: {ttl_minutes} minutes")

    def _create_key(self, odoo_url: str, username: str, scope: str) -> str:
        """
        Create unique cache key including scope hash.

        Different scopes for same user = different pool entries
        This ensures users with different permissions don't accidentally
        share connection objects.

        Args:
            odoo_url: Odoo instance URL
            username: Username
            scope: Scope string (e.g., "res.partner:RWD,sale.order:RW")

        Returns:
            SHA256 hash of combined credentials
        """
        scope_hash = hashlib.sha256(scope.encode()).hexdigest()
        combined = f"{odoo_url}:{username}:{scope_hash}"
        key = hashlib.sha256(combined.encode()).hexdigest()
        return key

    def get(self, odoo_url: str, username: str, scope: str) -> Optional[Dict[str, Any]]:
        """
        Get cached connection if valid.

        Args:
            odoo_url: Odoo instance URL
            username: Username
            scope: Scope string

        Returns:
            Cached connection dict or None if not found/expired
        """
        with self.lock:
            key = self._create_key(odoo_url, username, scope)

            if key not in self.connections:
                return None

            cached = self.connections[key]

            # Check if connection is still valid
            if datetime.now() > cached["expires_at"]:
                logger.debug(f"Connection expired for {username}, removing from pool")
                del self.connections[key]
                return None

            logger.debug(f"Reusing cached connection for {username} (expires in {(cached['expires_at'] - datetime.now()).seconds}s)")
            return cached

    def set(
        self,
        odoo_url: str,
        username: str,
        scope: str,
        uid: int,
        db: str,
        models_proxy: xmlrpc_client.ServerProxy
    ) -> None:
        """
        Store connection in pool.

        Args:
            odoo_url: Odoo instance URL
            username: Username
            scope: Scope string
            uid: User ID from authentication
            db: Database name
            models_proxy: XML-RPC ServerProxy for object endpoint
        """
        with self.lock:
            key = self._create_key(odoo_url, username, scope)

            self.connections[key] = {
                "uid": uid,
                "db": db,
                "models_proxy": models_proxy,
                "scope": scope,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + self.max_age
            }

            logger.debug(f"Stored connection in pool for {username} (TTL: {self.max_age.total_seconds()}s)")

    def invalidate(self, odoo_url: str, username: str, scope: str) -> None:
        """
        Manually remove connection from pool (e.g., on logout).

        Args:
            odoo_url: Odoo instance URL
            username: Username
            scope: Scope string
        """
        with self.lock:
            key = self._create_key(odoo_url, username, scope)

            if key in self.connections:
                del self.connections[key]
                logger.debug(f"Invalidated cached connection for {username}")

    def size(self) -> int:
        """Get current pool size"""
        with self.lock:
            return len(self.connections)

    def stats(self) -> Dict[str, Any]:
        """
        Get pool statistics for monitoring.

        Returns:
            Dict with pool stats
        """
        with self.lock:
            expired_count = 0
            for conn in self.connections.values():
                if datetime.now() > conn["expires_at"]:
                    expired_count += 1

            return {
                "total_connections": len(self.connections),
                "expired_connections": expired_count,
                "active_connections": len(self.connections) - expired_count,
                "ttl_minutes": int(self.max_age.total_seconds() / 60)
            }

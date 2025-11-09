"""Odoo connection management with pool integration"""

import logging
from typing import Any, Dict, Tuple
from xmlrpc import client as xmlrpc_client

from .pool import ConnectionPool

logger = logging.getLogger(__name__)


class OdooConnectionError(Exception):
    """Raised when connection fails"""

    pass


class OdooConnectionManager:
    """
    Manages Odoo XML-RPC connections with pooling.

    Strategy:
    1. Check connection pool first
    2. If found and valid → return cached connection
    3. If not found → create new connection and cache it
    """

    def __init__(self, pool: ConnectionPool):
        """
        Initialize connection manager.

        Args:
            pool: ConnectionPool instance to use for caching
        """
        self.pool = pool

    def get_connection(
        self, odoo_url: str, odoo_db: str, username: str, password: str, scope: str
    ) -> Tuple[int, str, xmlrpc_client.ServerProxy]:
        """
        Get or create Odoo connection.

        Attempts to use cached connection from pool first.
        If cache miss, authenticates and stores in pool.

        Args:
            odoo_url: Odoo instance URL (e.g., https://company.odoo.com)
            odoo_db: Odoo database name
            username: Username for authentication
            password: Password for authentication
            scope: Scope string (used as part of cache key)

        Returns:
            Tuple of (uid, db, models_proxy) where:
            - uid: User ID from Odoo
            - db: Database name
            - models_proxy: XML-RPC ServerProxy for execute_kw calls

        Raises:
            OdooConnectionError: If authentication fails
        """

        # Check pool first
        cached = self.pool.get(odoo_url, username, scope)
        if cached:
            logger.debug(f"Using pooled connection for {username}")
            return cached["uid"], cached["db"], cached["models_proxy"]

        # Cache miss → create new connection
        logger.debug(f"No pooled connection, creating new connection for {username}")

        try:
            # Connect to common endpoint for authentication
            common = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/common")

            # Authenticate
            uid = common.authenticate(odoo_db, username, password, {})

            if not uid:
                raise OdooConnectionError(
                    "Authentication failed: Invalid username/password"
                )

            # Create models proxy for operations
            models = xmlrpc_client.ServerProxy(f"{odoo_url}/xmlrpc/2/object")

            # Store in pool
            self.pool.set(odoo_url, username, scope, uid, odoo_db, models)

            logger.debug(f"Successfully authenticated {username} (UID: {uid})")

            return uid, odoo_db, models

        except xmlrpc_client.Fault as e:
            raise OdooConnectionError(
                f"Odoo error during authentication: {e.faultString}"
            )
        except Exception as e:
            raise OdooConnectionError(f"Failed to connect to Odoo: {str(e)}")

    def invalidate_connection(self, odoo_url: str, username: str, scope: str) -> None:
        """
        Manually invalidate a cached connection.

        Useful for logout or credential refresh.

        Args:
            odoo_url: Odoo instance URL
            username: Username
            scope: Scope string
        """
        self.pool.invalidate(odoo_url, username, scope)
        logger.debug(f"Invalidated cached connection for {username}")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        return self.pool.stats()

    def get_pool_size(self) -> int:
        """Get number of connections in pool"""
        return self.pool.size()

"""Odoo XML-RPC client with scope validation"""
import logging
from typing import Any, List, Dict, Optional
from xmlrpc import client as xmlrpc_client

from ..auth.scope_validator import ScopeValidator
from ..connection.manager import OdooConnectionManager, OdooConnectionError

logger = logging.getLogger(__name__)

class OdooClientError(Exception):
    """Raised when Odoo operation fails"""
    pass

class OdooClient:
    """
    Odoo XML-RPC client with built-in scope validation.

    Every operation is validated against scope before execution.
    Raises PermissionError if operation is not allowed.
    """

    def __init__(
        self,
        odoo_url: str,
        odoo_db: str,
        username: str,
        password: str,
        connection_manager: OdooConnectionManager,
        scope_validator: ScopeValidator
    ):
        """
        Initialize Odoo client.

        Args:
            odoo_url: Odoo instance URL
            odoo_db: Database name
            username: Username
            password: Password
            connection_manager: OdooConnectionManager for connection pooling
            scope_validator: ScopeValidator for permission checking
        """
        self.odoo_url = odoo_url
        self.odoo_db = odoo_db
        self.username = username
        self.password = password
        self.connection_manager = connection_manager
        self.scope_validator = scope_validator

    async def _get_connection(self) -> tuple:
        """
        Get authenticated connection from pool or create new.

        Returns:
            Tuple of (uid, db, models_proxy)

        Raises:
            OdooClientError: If authentication fails
        """
        try:
            uid, db, models = self.connection_manager.get_connection(
                self.odoo_url,
                self.odoo_db,
                self.username,
                self.password,
                self.scope_validator.scope_string
            )
            return uid, db, models
        except OdooConnectionError as e:
            raise OdooClientError(str(e))

    async def execute_kw(
        self,
        model: str,
        method: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Execute Odoo RPC method with scope validation.

        This is the core method that all operations use.
        Validates scope before executing any operation.

        Args:
            model: Odoo model name (e.g., "res.partner")
            method: Method name (e.g., "search", "create")
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Result from Odoo

        Raises:
            PermissionError: If operation violates scope
            OdooClientError: If RPC call fails
        """
        args = args or []
        kwargs = kwargs or {}

        # Validate scope BEFORE executing
        try:
            self.scope_validator.enforce_call(model, method)
        except PermissionError as e:
            logger.warning(f"Permission denied for {self.username}: {str(e)}")
            raise

        # Get connection from pool
        try:
            uid, db, models = await self._get_connection()
        except OdooClientError as e:
            logger.error(f"Connection failed: {str(e)}")
            raise

        # Execute the RPC call
        try:
            logger.debug(f"Executing {model}.{method} for {self.username}")

            result = models.execute_kw(db, uid, self.password, model, method, args, kwargs)

            logger.debug(f"Successfully executed {model}.{method}")
            return result

        except xmlrpc_client.Fault as e:
            logger.error(f"Odoo RPC error: {e.faultString}")
            raise OdooClientError(f"Odoo error: {e.faultString}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise OdooClientError(f"RPC call failed: {str(e)}")

    # =========================================================================
    # High-level convenience methods
    # =========================================================================

    async def search(
        self,
        model: str,
        domain: Optional[List] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[int]:
        """
        Search for records.

        Args:
            model: Model name
            domain: Search domain
            limit: Max records
            offset: Skip records

        Returns:
            List of record IDs
        """
        domain = domain or []
        return await self.execute_kw(
            model,
            "search",
            [domain],
            {"limit": limit, "offset": offset}
        )

    async def read(
        self,
        model: str,
        ids: List[int],
        fields: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Read records.

        Args:
            model: Model name
            ids: Record IDs
            fields: Fields to read

        Returns:
            List of record dicts
        """
        fields = fields or []
        kwargs = {"fields": fields} if fields else {}
        return await self.execute_kw(model, "read", [ids], kwargs)

    async def search_read(
        self,
        model: str,
        domain: Optional[List] = None,
        fields: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search and read in one call.

        Args:
            model: Model name
            domain: Search domain
            fields: Fields to read
            limit: Max records
            offset: Skip records

        Returns:
            List of record dicts
        """
        domain = domain or []
        fields = fields or []
        return await self.execute_kw(
            model,
            "search_read",
            [domain],
            {"fields": fields, "limit": limit, "offset": offset}
        )

    async def search_count(
        self,
        model: str,
        domain: Optional[List] = None
    ) -> int:
        """
        Count matching records.

        Args:
            model: Model name
            domain: Search domain

        Returns:
            Count of records
        """
        domain = domain or []
        return await self.execute_kw(model, "search_count", [domain])

    async def fields_get(
        self,
        model: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get field definitions.

        Args:
            model: Model name
            fields: Specific fields to describe

        Returns:
            Field metadata
        """
        fields = fields or []
        kwargs = {"fields": fields} if fields else {}
        return await self.execute_kw(model, "fields_get", [fields], kwargs)

    async def default_get(
        self,
        model: str,
        fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get default values for fields.

        Args:
            model: Model name
            fields: Fields to get defaults for

        Returns:
            Default values dict
        """
        fields = fields or []
        return await self.execute_kw(model, "default_get", [fields])

    async def create(self, model: str, values: Dict[str, Any]) -> int:
        """
        Create a new record.

        Args:
            model: Model name
            values: Field values

        Returns:
            ID of created record
        """
        return await self.execute_kw(model, "create", [values])

    async def write(self, model: str, ids: List[int], values: Dict[str, Any]) -> bool:
        """
        Update records.

        Args:
            model: Model name
            ids: Record IDs
            values: Field values to update

        Returns:
            True if successful
        """
        return await self.execute_kw(model, "write", [ids, values])

    async def unlink(self, model: str, ids: List[int]) -> bool:
        """
        Delete records.

        Args:
            model: Model name
            ids: Record IDs

        Returns:
            True if successful
        """
        return await self.execute_kw(model, "unlink", [ids])

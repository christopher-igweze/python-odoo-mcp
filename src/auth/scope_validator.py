"""Scope validation and permission checking"""

import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ScopeValidationError(Exception):
    """Raised when scope validation fails"""

    pass


class ScopeValidator:
    """
    Validates and enforces scope-based permissions.

    Scope format: "model:PERMISSIONS,model:PERMISSIONS"
    Examples:
        - "res.partner:RWD"           ← Full access to res.partner
        - "sale.order:RW"             ← Can search/read/write, no delete
        - "product.product:R"         ← Read-only access
        - "*:R"                       ← Read-only access to all models
        - "*:RWD,res.partner:"        ← Full access to all except res.partner (denied)
        - "res.partner:RWD,sale.order:RW,*:R" ← Specific + wildcard

    Permissions:
        R = Read   (search, read, search_read, search_count, fields_get, default_get)
        W = Write  (write, create)
        D = Delete (unlink)
    """

    # Map operations to required permissions
    OPERATION_PERMISSIONS = {
        # Read operations
        "search": "R",
        "read": "R",
        "search_read": "R",
        "search_count": "R",
        "fields_get": "R",
        "default_get": "R",
        # Write operations
        "write": "W",
        "create": "W",
        # Delete operations
        "unlink": "D",
    }

    def __init__(self, scope_string: str):
        """
        Parse and initialize scope.

        Args:
            scope_string: Scope definition (e.g., "res.partner:RWD,sale.order:RW,*:R")

        Raises:
            ScopeValidationError: If scope format is invalid
        """
        self.scope_string = scope_string
        self.allowed_models: Dict[str, Set[str]] = {}
        self._parse_scope(scope_string)

    def _parse_scope(self, scope_string: str) -> None:
        """
        Parse scope string into allowed_models dict.

        Sets self.allowed_models to:
        {
            "res.partner": {"R", "W", "D"},
            "sale.order": {"R", "W"},
            "*": {"R"}
        }

        Also handles explicit denials:
        "model:" (no permissions) = deny access to that model

        Args:
            scope_string: Raw scope string to parse

        Raises:
            ScopeValidationError: If format is invalid
        """
        if not scope_string or not scope_string.strip():
            raise ScopeValidationError("Scope string cannot be empty")

        self.allowed_models = {}

        # Split by comma to get model:permission pairs
        pairs = scope_string.split(",")

        for pair in pairs:
            pair = pair.strip()

            if not pair:
                continue

            if ":" not in pair:
                logger.warning(f"Invalid scope pair (missing colon): {pair}")
                continue

            # Split by first colon only (model name might contain special chars)
            parts = pair.split(":", 1)
            model = parts[0].strip()
            perms_str = parts[1].strip() if len(parts) > 1 else ""

            if not model:
                logger.warning(f"Invalid scope pair (empty model): {pair}")
                continue

            # Convert permission string to set
            # "RWD" → {"R", "W", "D"}
            # "" → {} (explicit denial)
            perms = set(perms_str.upper())

            # Validate permissions
            valid_perms = {"R", "W", "D"}
            invalid = perms - valid_perms

            if invalid:
                logger.warning(f"Invalid permissions in scope '{model}': {invalid}")
                # Filter out invalid ones instead of failing
                perms = perms & valid_perms

            self.allowed_models[model] = perms

        logger.debug(f"Parsed scope: {self.allowed_models}")

        if not self.allowed_models:
            raise ScopeValidationError(
                "Scope string resulted in no valid model permissions"
            )

    def can_call(self, model: str, operation: str) -> bool:
        """
        Check if user has permission to call operation on model.

        Logic:
        1. Check exact model match
        2. If exact match found but empty set → deny
        3. If exact match found with permission → allow
        4. If no exact match, check wildcard "*"
        5. If neither → deny

        Args:
            model: Odoo model name (e.g., "res.partner")
            operation: Operation name (e.g., "search", "write")

        Returns:
            True if permission is granted, False otherwise
        """
        required_perm = self.OPERATION_PERMISSIONS.get(operation)

        if required_perm is None:
            logger.warning(f"Unknown operation: {operation}")
            return False

        # Check exact model match
        if model in self.allowed_models:
            return required_perm in self.allowed_models[model]

        # Check wildcard
        if "*" in self.allowed_models:
            return required_perm in self.allowed_models["*"]

        # No match = deny
        return False

    def enforce_call(self, model: str, operation: str) -> None:
        """
        Enforce permission, raising error if denied.

        Args:
            model: Odoo model name
            operation: Operation name

        Raises:
            PermissionError: If permission is denied
        """
        if not self.can_call(model, operation):
            required_perm = self.OPERATION_PERMISSIONS.get(operation, "?")
            raise PermissionError(
                f"Permission denied: No '{required_perm}' permission for operation '{operation}' on model '{model}'"
            )

    def get_accessible_models(self) -> Optional[List[str]]:
        """
        Get list of accessible models.

        Returns:
            List of model names if specific models are granted, or None if wildcard "*" is used
        """
        if "*" in self.allowed_models:
            return None  # User has access to all models

        return list(self.allowed_models.keys())

    def get_model_permissions(self, model: str) -> Set[str]:
        """
        Get permissions for a specific model.

        Args:
            model: Odoo model name

        Returns:
            Set of permission letters (e.g., {"R", "W", "D"})
        """
        if model in self.allowed_models:
            return self.allowed_models[model]

        if "*" in self.allowed_models:
            return self.allowed_models["*"]

        return set()  # No access

"""Unit tests for scope validation module"""
import pytest

from src.auth.scope_validator import ScopeValidator, ScopeValidationError


@pytest.mark.unit
class TestScopeValidatorParsing:
    """Test scope string parsing"""

    def test_parse_single_model_with_all_permissions(self):
        """Test parsing single model with all permissions"""
        validator = ScopeValidator("res.partner:RWD")
        assert validator.allowed_models == {"res.partner": {"R", "W", "D"}}

    def test_parse_single_model_read_only(self):
        """Test parsing single model with read-only permission"""
        validator = ScopeValidator("res.partner:R")
        assert validator.allowed_models == {"res.partner": {"R"}}

    def test_parse_multiple_models(self):
        """Test parsing multiple models with different permissions"""
        validator = ScopeValidator("res.partner:RWD,sale.order:RW,product.product:R")
        assert validator.allowed_models == {
            "res.partner": {"R", "W", "D"},
            "sale.order": {"R", "W"},
            "product.product": {"R"}
        }

    def test_parse_wildcard_all_permissions(self):
        """Test parsing wildcard with all permissions"""
        validator = ScopeValidator("*:RWD")
        assert validator.allowed_models == {"*": {"R", "W", "D"}}

    def test_parse_wildcard_read_only(self):
        """Test parsing wildcard with read-only"""
        validator = ScopeValidator("*:R")
        assert validator.allowed_models == {"*": {"R"}}

    def test_parse_mixed_specific_and_wildcard(self):
        """Test parsing specific models and wildcard together"""
        validator = ScopeValidator("res.partner:RWD,*:R")
        assert validator.allowed_models == {
            "res.partner": {"R", "W", "D"},
            "*": {"R"}
        }

    def test_parse_explicit_denial(self):
        """Test parsing explicit denial (empty permissions)"""
        validator = ScopeValidator("res.partner:")
        assert validator.allowed_models == {"res.partner": set()}

    def test_parse_ignores_invalid_permissions(self):
        """Test that invalid permissions are filtered out"""
        validator = ScopeValidator("res.partner:RWX")
        # X is invalid, should be filtered
        assert validator.allowed_models == {"res.partner": {"R", "W"}}

    def test_parse_empty_scope_raises_error(self):
        """Test that empty scope raises ScopeValidationError"""
        with pytest.raises(ScopeValidationError):
            ScopeValidator("")

    def test_parse_whitespace_only_raises_error(self):
        """Test that whitespace-only scope raises error"""
        with pytest.raises(ScopeValidationError):
            ScopeValidator("   ")

    def test_parse_with_whitespace_is_trimmed(self):
        """Test that whitespace around values is trimmed"""
        validator = ScopeValidator("  res.partner : RWD  ,  sale.order : RW  ")
        assert "res.partner" in validator.allowed_models
        assert "sale.order" in validator.allowed_models


@pytest.mark.unit
class TestScopeValidatorPermissionChecking:
    """Test permission checking logic"""

    def test_can_call_exact_model_match(self):
        """Test permission check with exact model match"""
        validator = ScopeValidator("res.partner:RWD")

        assert validator.can_call("res.partner", "search") is True  # R
        assert validator.can_call("res.partner", "read") is True    # R
        assert validator.can_call("res.partner", "write") is True   # W
        assert validator.can_call("res.partner", "create") is True  # W
        assert validator.can_call("res.partner", "unlink") is True  # D

    def test_can_call_denied_operation(self):
        """Test permission check for denied operation"""
        validator = ScopeValidator("res.partner:RW")

        assert validator.can_call("res.partner", "unlink") is False  # D not granted

    def test_can_call_wildcard_fallback(self):
        """Test permission check falls back to wildcard"""
        validator = ScopeValidator("*:R")

        assert validator.can_call("res.partner", "search") is True
        assert validator.can_call("sale.order", "read") is True
        assert validator.can_call("random.model", "search_read") is True

    def test_can_call_wildcard_respects_permissions(self):
        """Test wildcard respects permission levels"""
        validator = ScopeValidator("*:R")

        assert validator.can_call("res.partner", "search") is True
        assert validator.can_call("res.partner", "write") is False
        assert validator.can_call("res.partner", "unlink") is False

    def test_can_call_specific_overrides_wildcard(self):
        """Test that specific model permissions override wildcard"""
        validator = ScopeValidator("res.partner:RWD,*:R")

        # res.partner has full access
        assert validator.can_call("res.partner", "unlink") is True
        # Other models have read-only
        assert validator.can_call("sale.order", "unlink") is False

    def test_can_call_explicit_denial(self):
        """Test explicit denial takes precedence"""
        validator = ScopeValidator("res.partner:,*:RWD")

        # res.partner is explicitly denied
        assert validator.can_call("res.partner", "search") is False
        # Other models allowed
        assert validator.can_call("sale.order", "search") is True

    def test_can_call_unknown_operation_denied(self):
        """Test that unknown operations are denied"""
        validator = ScopeValidator("*:RWD")

        assert validator.can_call("res.partner", "unknown_operation") is False

    def test_enforce_call_raises_permission_error(self):
        """Test that enforce_call raises PermissionError on denial"""
        validator = ScopeValidator("res.partner:R")

        with pytest.raises(PermissionError):
            validator.enforce_call("res.partner", "unlink")

    def test_enforce_call_passes_on_grant(self):
        """Test that enforce_call passes on permission grant"""
        validator = ScopeValidator("res.partner:RWD")

        # Should not raise
        validator.enforce_call("res.partner", "unlink")


@pytest.mark.unit
class TestScopeValidatorAccessibleModels:
    """Test accessible models retrieval"""

    def test_get_accessible_models_with_wildcard(self):
        """Test that wildcard returns None (access to all)"""
        validator = ScopeValidator("*:R")
        assert validator.get_accessible_models() is None

    def test_get_accessible_models_specific(self):
        """Test retrieving specific accessible models"""
        validator = ScopeValidator("res.partner:RWD,sale.order:RW")
        models = validator.get_accessible_models()

        assert models is not None
        assert set(models) == {"res.partner", "sale.order"}

    def test_get_model_permissions(self):
        """Test retrieving permissions for specific model"""
        validator = ScopeValidator("res.partner:RWD,sale.order:RW,*:R")

        assert validator.get_model_permissions("res.partner") == {"R", "W", "D"}
        assert validator.get_model_permissions("sale.order") == {"R", "W"}
        assert validator.get_model_permissions("random.model") == {"R"}  # Falls back to wildcard
        assert validator.get_model_permissions("nonexistent") == {"R"}   # Falls back to wildcard

    def test_get_model_permissions_no_access(self):
        """Test retrieving permissions when no wildcard"""
        validator = ScopeValidator("res.partner:R")

        assert validator.get_model_permissions("sale.order") == set()  # No access

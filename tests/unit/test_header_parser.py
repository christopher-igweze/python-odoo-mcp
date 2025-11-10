"""Unit tests for authentication header parsing"""

import base64
import json

import pytest

from src.auth.header_parser import AuthenticationError, parse_auth_header


@pytest.mark.unit
class TestParseAuthHeaderSuccess:
    """Test successful header parsing"""

    def test_parse_valid_auth_header(self):
        """Test parsing valid auth header"""
        creds = {
            "url": "https://company.odoo.com",
            "database": "company_db",
            "username": "api_user",
            "password": "secret123",
            "scope": "res.partner:RWD",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        result = parse_auth_header(header)

        assert result["url"] == "https://company.odoo.com"
        assert result["database"] == "company_db"
        assert result["username"] == "api_user"
        assert result["password"] == "secret123"
        assert result["scope"] == "res.partner:RWD"

    def test_parse_header_with_multiple_scopes(self):
        """Test parsing header with multiple scope entries"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:RWD,sale.order:RW,*:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        result = parse_auth_header(header)

        assert result["scope"] == "res.partner:RWD,sale.order:RW,*:R"

    def test_parse_header_with_whitespace_in_fields(self):
        """Test parsing trims whitespace from most fields"""
        creds = {
            "url": "  https://example.odoo.com  ",
            "database": "  mydb  ",
            "username": "  user1  ",
            "password": "  pass123  ",
            "scope": "  res.partner:R  ",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        result = parse_auth_header(header)

        assert result["url"] == "https://example.odoo.com"
        assert result["database"] == "mydb"
        assert result["username"] == "user1"
        assert result["password"] == "  pass123  "  # Password not trimmed
        assert result["scope"] == "res.partner:R"

    def test_parse_header_preserves_password_whitespace(self):
        """Test parsing preserves spaces in password intentionally"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "pass with spaces",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        result = parse_auth_header(header)

        assert result["password"] == "pass with spaces"

    def test_parse_header_with_special_characters_in_password(self):
        """Test parsing handles special characters in password"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "p@ssw0rd!#$%^&*()",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        result = parse_auth_header(header)

        assert result["password"] == "p@ssw0rd!#$%^&*()"

    def test_parse_header_with_unicode_in_username(self):
        """Test parsing handles unicode characters"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user_ñame",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode("utf-8")).decode()

        result = parse_auth_header(header)

        assert result["username"] == "user_ñame"


@pytest.mark.unit
class TestParseAuthHeaderErrors:
    """Test error handling"""

    def test_parse_empty_header_raises_error(self):
        """Test empty header raises AuthenticationError"""
        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header("")

        assert "Missing X-Auth-Credentials header" in str(exc_info.value)

    def test_parse_none_header_raises_error(self):
        """Test None header raises AuthenticationError"""
        with pytest.raises(AuthenticationError):
            parse_auth_header(None)

    def test_parse_whitespace_only_header_raises_error(self):
        """Test whitespace-only header raises error"""
        with pytest.raises(AuthenticationError):
            parse_auth_header("   ")

    def test_parse_invalid_base64_raises_error(self):
        """Test invalid base64 raises AuthenticationError"""
        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header("not valid base64!!!")

        assert "Invalid base64 encoding" in str(exc_info.value)

    def test_parse_invalid_json_raises_error(self):
        """Test invalid JSON raises AuthenticationError"""
        invalid_json = base64.b64encode(b"not json").decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(invalid_json)

        assert "Invalid JSON" in str(exc_info.value)

    def test_parse_invalid_utf8_raises_error(self):
        """Test invalid UTF-8 raises AuthenticationError"""
        # Create invalid UTF-8 byte sequence
        invalid_utf8 = base64.b64encode(b"\x80\x81\x82").decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(invalid_utf8)

        assert "Invalid UTF-8" in str(exc_info.value)


@pytest.mark.unit
class TestParseAuthHeaderMissingFields:
    """Test missing required fields"""

    def test_parse_header_missing_url_raises_error(self):
        """Test missing url field raises error"""
        creds = {
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "Missing required fields" in str(exc_info.value)
        assert "url" in str(exc_info.value)

    def test_parse_header_missing_database_raises_error(self):
        """Test missing database field raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "Missing required fields" in str(exc_info.value)
        assert "database" in str(exc_info.value)

    def test_parse_header_missing_username_raises_error(self):
        """Test missing username field raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "Missing required fields" in str(exc_info.value)
        assert "username" in str(exc_info.value)

    def test_parse_header_missing_password_raises_error(self):
        """Test missing password field raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "Missing required fields" in str(exc_info.value)
        assert "password" in str(exc_info.value)

    def test_parse_header_missing_scope_raises_error(self):
        """Test missing scope field raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "pass",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "Missing required fields" in str(exc_info.value)
        assert "scope" in str(exc_info.value)

    def test_parse_header_missing_multiple_fields_raises_error(self):
        """Test missing multiple fields reports all of them"""
        creds = {
            "url": "https://example.odoo.com",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        error_msg = str(exc_info.value)
        assert "database" in error_msg
        assert "username" in error_msg
        assert "password" in error_msg
        assert "scope" in error_msg


@pytest.mark.unit
class TestParseAuthHeaderEmptyFields:
    """Test empty or whitespace-only fields"""

    def test_parse_header_empty_url_raises_error(self):
        """Test empty url field raises error"""
        creds = {
            "url": "",
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_whitespace_only_url_raises_error(self):
        """Test whitespace-only url raises error"""
        creds = {
            "url": "   ",
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_empty_database_raises_error(self):
        """Test empty database field raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_empty_username_raises_error(self):
        """Test empty username raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_empty_password_raises_error(self):
        """Test empty password raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_empty_scope_raises_error(self):
        """Test empty scope raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)


@pytest.mark.unit
class TestParseAuthHeaderInvalidTypes:
    """Test fields with invalid types"""

    def test_parse_header_non_string_url_raises_error(self):
        """Test non-string url raises error"""
        creds = {
            "url": 123,
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_non_string_database_raises_error(self):
        """Test non-string database raises error"""
        creds = {
            "url": "https://example.odoo.com",
            "database": None,
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

    def test_parse_header_list_instead_of_string_raises_error(self):
        """Test list value instead of string raises error"""
        creds = {
            "url": ["https://example.odoo.com"],
            "database": "db",
            "username": "user",
            "password": "pass",
            "scope": "res.partner:R",
        }
        header = base64.b64encode(json.dumps(creds).encode()).decode()

        with pytest.raises(AuthenticationError) as exc_info:
            parse_auth_header(header)

        assert "non-empty string" in str(exc_info.value)

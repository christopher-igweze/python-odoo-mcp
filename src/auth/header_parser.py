"""Parse authentication credentials from request headers"""
import base64
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Raised when authentication data is invalid"""
    pass

def parse_auth_header(header_value: str) -> Dict[str, Any]:
    """
    Parse X-Auth-Credentials header.

    Expected format:
    X-Auth-Credentials: base64(JSON)

    Decoded JSON should contain:
    {
        "url": "https://company.odoo.com",
        "database": "company_db",
        "username": "api_user",
        "password": "secret123",
        "scope": "res.partner:RWD,sale.order:RW,*:R"
    }

    Args:
        header_value: Base64-encoded JSON string from header

    Returns:
        Dict with keys: url, database, username, password, scope

    Raises:
        AuthenticationError: If header is invalid or missing required fields
    """

    if not header_value:
        raise AuthenticationError("Missing X-Auth-Credentials header")

    try:
        # Decode base64
        decoded_bytes = base64.b64decode(header_value.strip())
        decoded_str = decoded_bytes.decode('utf-8')

        # Parse JSON
        creds = json.loads(decoded_str)

        # Validate required fields
        required_fields = ["url", "database", "username", "password", "scope"]
        missing_fields = [f for f in required_fields if f not in creds]

        if missing_fields:
            raise AuthenticationError(
                f"Missing required fields in X-Auth-Credentials: {', '.join(missing_fields)}"
            )

        # Validate non-empty strings
        for field in required_fields:
            if not isinstance(creds[field], str) or not creds[field].strip():
                raise AuthenticationError(f"Field '{field}' must be a non-empty string")

        logger.debug(f"Successfully parsed credentials for user: {creds['username']}")

        return {
            "url": creds["url"].strip(),
            "database": creds["database"].strip(),
            "username": creds["username"].strip(),
            "password": creds["password"],  # Don't strip password, spaces may be intentional
            "scope": creds["scope"].strip()
        }

    except base64.binascii.Error as e:
        raise AuthenticationError(f"Invalid base64 encoding in X-Auth-Credentials: {str(e)}")
    except json.JSONDecodeError as e:
        raise AuthenticationError(f"Invalid JSON in X-Auth-Credentials: {str(e)}")
    except UnicodeDecodeError as e:
        raise AuthenticationError(f"Invalid UTF-8 encoding in X-Auth-Credentials: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Failed to parse X-Auth-Credentials: {str(e)}")

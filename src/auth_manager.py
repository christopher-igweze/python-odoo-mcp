"""Authentication and encryption module for API keys"""

import json
import logging
from typing import Any, Dict

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel, Field

from src.config import config

logger = logging.getLogger(__name__)


def _get_key_fingerprint(key: bytes) -> str:
    """Get a short fingerprint of the encryption key for logging"""
    # Show first 8 and last 8 characters of the base64 key
    key_str = key.decode() if isinstance(key, bytes) else key
    return f"{key_str[:8]}...{key_str[-8:]}"


class Credentials(BaseModel):
    """Odoo credentials model"""

    url: str = Field(..., description="Odoo instance URL")
    database: str = Field(..., description="Odoo database name")
    username: str = Field(..., description="Odoo username")
    password: str = Field(..., description="Odoo password")
    scope: str = Field(default="*:R", description="Permission scope")


class APIKeyResponse(BaseModel):
    """API key response model"""

    api_key: str = Field(..., description="Encrypted API key for future requests")
    credentials: Dict[str, Any] = Field(
        ..., description="Decrypted credential info (password excluded)"
    )


class EncryptionManager:
    """Handles encryption and decryption of API keys"""

    def __init__(self):
        """Initialize encryption manager with encryption key"""
        try:
            self.cipher = Fernet(config.ENCRYPTION_KEY)
            key_fp = _get_key_fingerprint(config.ENCRYPTION_KEY)
            logger.debug(f"✓ Encryption manager initialized (key: {key_fp})")
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise

    def encrypt_credentials(self, credentials: Credentials) -> str:
        """
        Encrypt credentials into an API key

        Args:
            credentials: Odoo credentials

        Returns:
            Encrypted API key as string

        Raises:
            Exception: If encryption fails
        """
        try:
            # Convert credentials to JSON
            creds_json = json.dumps(
                {
                    "url": credentials.url,
                    "database": credentials.database,
                    "username": credentials.username,
                    "password": credentials.password,
                    "scope": credentials.scope,
                }
            )

            # Encrypt the JSON
            encrypted = self.cipher.encrypt(creds_json.encode())
            api_key = encrypted.decode()

            logger.debug(f"✓ Credentials encrypted for user: {credentials.username}")
            return api_key

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_credentials(self, api_key: str) -> Dict[str, Any]:
        """
        Decrypt an API key back to credentials

        Args:
            api_key: Encrypted API key

        Returns:
            Decrypted credentials dictionary

        Raises:
            ValueError: If decryption fails or key is invalid
        """
        try:
            # Decrypt the API key
            decrypted = self.cipher.decrypt(api_key.encode())
            credentials = json.loads(decrypted.decode())

            logger.debug(
                f"✓ Credentials decrypted for user: {credentials.get('username', 'unknown')}"
            )
            return credentials

        except InvalidToken:
            current_key_fp = _get_key_fingerprint(config.ENCRYPTION_KEY)
            api_key_sample = api_key[:32] + "..." if len(api_key) > 32 else api_key
            logger.error(
                f"Invalid API key: decryption failed. "
                f"Current encryption key: {current_key_fp}. "
                f"API key sample: {api_key_sample}. "
                f"This usually means the API key was generated with a different encryption key. "
                f"Ensure ENCRYPTION_KEY environment variable is set to the same value used when the key was generated."
            )
            raise ValueError("Invalid API key")
        except json.JSONDecodeError:
            logger.error("API key corrupted: invalid JSON after decryption")
            raise ValueError("Corrupted API key")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt API key: {e}")

    def get_credential_info(self, api_key: str) -> Dict[str, Any]:
        """
        Get credential info from API key (without password)

        Args:
            api_key: Encrypted API key

        Returns:
            Credential info dict without password
        """
        creds = self.decrypt_credentials(api_key)
        return {
            "url": creds["url"],
            "database": creds["database"],
            "username": creds["username"],
            "scope": creds["scope"],
        }


# Global encryption manager instance
encryption_manager = EncryptionManager()

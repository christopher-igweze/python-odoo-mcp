"""Configuration management for MCP Server"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def _get_key_fingerprint(key: bytes) -> str:
    """Get a short fingerprint of the encryption key for logging"""
    # Show first 8 and last 8 characters of the base64 key
    key_str = key.decode() if isinstance(key, bytes) else key
    return f"{key_str[:8]}...{key_str[-8:]}"


def _init_encryption_key() -> bytes:
    """Initialize and validate encryption key"""
    encryption_key_env = os.getenv("ENCRYPTION_KEY", "").strip()

    if encryption_key_env:
        # If env var is set, validate it's a proper Fernet key
        try:
            # Fernet keys must be 32 url-safe base64-encoded bytes
            key = (
                encryption_key_env.encode()
                if isinstance(encryption_key_env, str)
                else encryption_key_env
            )
            # Validate by attempting to create a Fernet instance
            Fernet(key)
            logger.info(
                f"✓ Using persistent ENCRYPTION_KEY from environment (fingerprint: {_get_key_fingerprint(key)})"
            )
            return key
        except Exception as e:
            raise ValueError(
                f'Invalid ENCRYPTION_KEY: {str(e)}. Key must be a valid Fernet key generated with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
    else:
        # Generate a new key if not provided
        new_key = Fernet.generate_key()
        logger.warning(
            f"⚠️  NO ENCRYPTION_KEY set in environment. Generated temporary key (fingerprint: {_get_key_fingerprint(new_key)}). "
            f"This will cause API keys to become invalid on restart. Set ENCRYPTION_KEY env var for production!"
        )
        return new_key


class Config:
    """Application configuration from environment variables"""

    # Connection pool settings
    CONNECTION_POOL_TTL_MINUTES: int = int(
        os.getenv("CONNECTION_POOL_TTL_MINUTES", "60")
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "3000"))

    # Encryption key for API key generation
    # If provided via env, validate it; otherwise generate a new one
    ENCRYPTION_KEY: bytes = _init_encryption_key()

    @classmethod
    def validate(cls) -> None:
        """Validate configuration on startup"""
        if cls.CONNECTION_POOL_TTL_MINUTES < 1:
            raise ValueError("CONNECTION_POOL_TTL_MINUTES must be >= 1")

        if cls.LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}")


config = Config()

"""Configuration management for MCP Server"""
import os
from typing import Optional
from cryptography.fernet import Fernet

class Config:
    """Application configuration from environment variables"""

    # Connection pool settings
    CONNECTION_POOL_TTL_MINUTES: int = int(os.getenv("CONNECTION_POOL_TTL_MINUTES", "60"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "3000"))

    # Encryption key for API key generation
    # If provided via env, use it; otherwise generate a new one
    _encryption_key_env = os.getenv("ENCRYPTION_KEY")
    ENCRYPTION_KEY: bytes = _encryption_key_env.encode() if isinstance(_encryption_key_env, str) else (_encryption_key_env if _encryption_key_env else Fernet.generate_key())

    @classmethod
    def validate(cls) -> None:
        """Validate configuration on startup"""
        if cls.CONNECTION_POOL_TTL_MINUTES < 1:
            raise ValueError("CONNECTION_POOL_TTL_MINUTES must be >= 1")

        if cls.LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError(f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}")

config = Config()

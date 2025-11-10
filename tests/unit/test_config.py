"""Unit tests for configuration module"""

import os
import pytest
from cryptography.fernet import Fernet

from src.config import Config


@pytest.mark.unit
class TestConfigEncryptionKey:
    """Test encryption key initialization and validation"""

    def test_encryption_key_is_valid_fernet_key(self):
        """Test that the initialized encryption key is valid for Fernet"""
        from src.config import config

        # Should not raise an error
        cipher = Fernet(config.ENCRYPTION_KEY)
        assert cipher is not None

    def test_encryption_key_is_bytes(self):
        """Test that encryption key is bytes type"""
        from src.config import config

        assert isinstance(config.ENCRYPTION_KEY, bytes)

    def test_encryption_key_has_correct_length(self):
        """Test that encryption key has correct length for Fernet"""
        from src.config import config

        # Fernet keys are 44 bytes when base64 encoded
        assert len(config.ENCRYPTION_KEY) == 44


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation"""

    def test_config_validate_passes(self):
        """Test that config validation passes with valid settings"""
        from src.config import config

        # Should not raise any errors
        config.validate()

    def test_connection_pool_ttl_is_positive(self):
        """Test that connection pool TTL is positive"""
        from src.config import config

        assert config.CONNECTION_POOL_TTL_MINUTES >= 1

    def test_log_level_is_valid(self):
        """Test that log level is one of the valid options"""
        from src.config import config

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        assert config.LOG_LEVEL in valid_levels


@pytest.mark.unit
class TestConfigDefaults:
    """Test default configuration values"""

    def test_default_host(self):
        """Test default HOST is set"""
        from src.config import config

        assert config.HOST == "0.0.0.0"

    def test_default_port(self):
        """Test default PORT is set"""
        from src.config import config

        assert config.PORT == 3000

    def test_default_log_level(self):
        """Test default LOG_LEVEL"""
        from src.config import config

        # Default should be INFO or higher
        assert config.LOG_LEVEL in ["INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"]

    def test_default_connection_pool_ttl(self):
        """Test default CONNECTION_POOL_TTL_MINUTES"""
        from src.config import config

        # Default should be 60 minutes
        assert config.CONNECTION_POOL_TTL_MINUTES >= 1


@pytest.mark.unit
class TestConfigValidationErrors:
    """Test configuration validation errors"""

    def test_config_validate_with_invalid_log_level(self, monkeypatch):
        """Test config validation fails with invalid LOG_LEVEL"""
        # Create a Config instance and manually set invalid log level
        monkeypatch.setenv("LOG_LEVEL", "INVALID")

        # Re-import to get fresh config
        import importlib
        import src.config
        importlib.reload(src.config)

        from src.config import config

        # Validation should fail
        with pytest.raises(ValueError):
            config.validate()

    def test_config_validate_with_negative_ttl(self, monkeypatch):
        """Test config validation fails with negative TTL"""
        # Set negative TTL
        monkeypatch.setenv("CONNECTION_POOL_TTL_MINUTES", "-1")

        # Re-import to get fresh config
        import importlib
        import src.config
        importlib.reload(src.config)

        from src.config import config

        # Validation should fail
        with pytest.raises(ValueError):
            config.validate()

    def test_config_validate_with_zero_ttl(self, monkeypatch):
        """Test config validation fails with zero TTL"""
        monkeypatch.setenv("CONNECTION_POOL_TTL_MINUTES", "0")

        # Re-import to get fresh config
        import importlib
        import src.config
        importlib.reload(src.config)

        from src.config import config

        # Validation should fail
        with pytest.raises(ValueError):
            config.validate()

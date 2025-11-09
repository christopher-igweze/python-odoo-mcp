"""Unit tests for encryption module"""
import pytest
import json

from src.auth_manager import EncryptionManager, Credentials
from cryptography.fernet import Fernet


@pytest.mark.unit
class TestEncryptionManager:
    """Test EncryptionManager encryption and decryption"""

    @pytest.fixture
    def encryption_manager(self):
        """Create a test encryption manager with a fresh key"""
        return EncryptionManager()

    def test_encryption_manager_initialization(self, encryption_manager):
        """Test that EncryptionManager initializes correctly"""
        assert encryption_manager is not None
        assert encryption_manager.cipher is not None

    def test_encrypt_credentials(self, encryption_manager):
        """Test that credentials are encrypted correctly"""
        creds = Credentials(
            url="https://test.odoo.com",
            database="test_db",
            username="test_user",
            password="test_password",
            scope="*:RWD"
        )

        encrypted = encryption_manager.encrypt_credentials(creds)

        # Should return a string
        assert isinstance(encrypted, str)
        # Should not be empty
        assert len(encrypted) > 0
        # Should not contain plaintext password
        assert "test_password" not in encrypted

    def test_decrypt_credentials(self, encryption_manager):
        """Test that encrypted credentials can be decrypted"""
        original_creds = Credentials(
            url="https://test.odoo.com",
            database="test_db",
            username="test_user",
            password="test_password",
            scope="*:RWD"
        )

        encrypted = encryption_manager.encrypt_credentials(original_creds)
        decrypted = encryption_manager.decrypt_credentials(encrypted)

        assert decrypted["url"] == original_creds.url
        assert decrypted["database"] == original_creds.database
        assert decrypted["username"] == original_creds.username
        assert decrypted["password"] == original_creds.password
        assert decrypted["scope"] == original_creds.scope

    def test_decrypt_invalid_key_raises_error(self, encryption_manager):
        """Test that decrypting invalid key raises ValueError"""
        with pytest.raises(ValueError):
            encryption_manager.decrypt_credentials("invalid_encrypted_key")

    def test_get_credential_info_without_password(self, encryption_manager):
        """Test that credential info excludes password"""
        creds = Credentials(
            url="https://test.odoo.com",
            database="test_db",
            username="test_user",
            password="test_password",
            scope="*:RWD"
        )

        encrypted = encryption_manager.encrypt_credentials(creds)
        info = encryption_manager.get_credential_info(encrypted)

        assert info["url"] == creds.url
        assert info["database"] == creds.database
        assert info["username"] == creds.username
        assert info["scope"] == creds.scope
        assert "password" not in info

    def test_roundtrip_encryption_decryption(self, encryption_manager):
        """Test multiple encrypt/decrypt cycles"""
        original = Credentials(
            url="https://example.com",
            database="db1",
            username="user1",
            password="pass123",
            scope="res.partner:RWD"
        )

        # Encrypt multiple times
        encrypted1 = encryption_manager.encrypt_credentials(original)
        encrypted2 = encryption_manager.encrypt_credentials(original)

        # Different encryption each time (due to Fernet's random IV)
        assert encrypted1 != encrypted2

        # Both decrypt to the same values
        decrypted1 = encryption_manager.decrypt_credentials(encrypted1)
        decrypted2 = encryption_manager.decrypt_credentials(encrypted2)

        assert decrypted1 == decrypted2
        assert decrypted1["username"] == original.username

    def test_different_scopes_are_preserved(self, encryption_manager):
        """Test that different scopes are preserved during encryption"""
        scopes = [
            "*:R",
            "*:RWD",
            "res.partner:RWD",
            "res.partner:RWD,sale.order:RW,*:R"
        ]

        for scope in scopes:
            creds = Credentials(
                url="https://test.odoo.com",
                database="test_db",
                username="test_user",
                password="test_password",
                scope=scope
            )

            encrypted = encryption_manager.encrypt_credentials(creds)
            decrypted = encryption_manager.decrypt_credentials(encrypted)

            assert decrypted["scope"] == scope

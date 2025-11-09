"""Integration tests for authentication endpoints"""
import pytest
import json

from src.auth_manager import Credentials


@pytest.mark.integration
class TestAuthGenerateEndpoint:
    """Test /auth/generate endpoint"""

    def test_generate_api_key_success(self, test_client, test_credentials):
        """Test successful API key generation"""
        payload = {
            "url": test_credentials.url,
            "database": test_credentials.database,
            "username": test_credentials.username,
            "password": test_credentials.password,
            "scope": test_credentials.scope
        }

        response = test_client.post("/auth/generate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert "credentials" in data
        assert data["credentials"]["username"] == test_credentials.username
        assert "password" not in data["credentials"]

    def test_generate_api_key_missing_field(self, test_client):
        """Test API key generation with missing required field"""
        payload = {
            "url": "https://test.odoo.com",
            "database": "test_db",
            # Missing username
            "password": "test_password",
            "scope": "*:R"
        }

        response = test_client.post("/auth/generate", json=payload)
        assert response.status_code == 422  # Validation error

    def test_generate_api_key_returns_no_password(self, test_client, test_credentials):
        """Test that generated API key response doesn't include password"""
        payload = {
            "url": test_credentials.url,
            "database": test_credentials.database,
            "username": test_credentials.username,
            "password": test_credentials.password,
            "scope": test_credentials.scope
        }

        response = test_client.post("/auth/generate", json=payload)
        data = response.json()

        assert "password" not in data["credentials"]
        assert data["credentials"]["username"] == test_credentials.username


@pytest.mark.integration
class TestAuthValidateEndpoint:
    """Test /auth/validate endpoint"""

    def test_validate_api_key_success(self, test_client, test_api_key):
        """Test successful API key validation"""
        payload = {"api_key": test_api_key}

        response = test_client.post("/auth/validate", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "valid"
        assert "credentials" in data
        assert "password" not in data["credentials"]

    def test_validate_api_key_invalid(self, test_client):
        """Test validation with invalid API key"""
        payload = {"api_key": "invalid_key_here"}

        response = test_client.post("/auth/validate", json=payload)
        assert response.status_code == 401

    def test_validate_api_key_missing(self, test_client):
        """Test validation with missing API key"""
        payload = {}

        response = test_client.post("/auth/validate", json=payload)
        assert response.status_code == 400

    def test_validate_api_key_returns_credential_info(self, test_client, test_api_key, test_credentials):
        """Test that validation returns correct credential info"""
        payload = {"api_key": test_api_key}

        response = test_client.post("/auth/validate", json=payload)
        data = response.json()

        credentials = data["credentials"]
        assert credentials["username"] == test_credentials.username
        assert credentials["scope"] == test_credentials.scope
        assert "password" not in credentials

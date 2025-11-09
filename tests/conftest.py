"""Shared pytest fixtures and configuration"""
import pytest
from starlette.testclient import TestClient
from httpx import AsyncClient
from cryptography.fernet import Fernet

from src.server import app
from src.config import config
from src.auth_manager import encryption_manager, Credentials


@pytest.fixture(scope="session")
def test_encryption_key():
    """Generate a test encryption key"""
    return Fernet.generate_key()


@pytest.fixture(scope="session")
def test_credentials():
    """Create test credentials"""
    return Credentials(
        url="https://demo.odoo.com",
        database="demo",
        username="test_user",
        password="test_password",
        scope="res.partner:RWD,sale.order:RW,*:R"
    )


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
async def async_test_client():
    """Create an async test client for the FastAPI app"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_api_key(test_credentials):
    """Generate a test API key from test credentials"""
    return encryption_manager.encrypt_credentials(test_credentials)


@pytest.fixture
def mock_odoo_credentials():
    """Mock Odoo credentials for testing"""
    return {
        "url": "https://demo.odoo.com",
        "database": "demo",
        "username": "admin",
        "password": "admin",
        "scope": "*:RWD"
    }

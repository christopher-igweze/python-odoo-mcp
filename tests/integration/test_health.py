"""Integration tests for health check endpoints"""

import pytest


@pytest.mark.integration
class TestHealthEndpoint:
    """Test /health endpoint"""

    def test_health_endpoint_returns_200(self, test_client):
        """Test that health endpoint returns 200"""
        response = test_client.get("/health")
        assert response.status_code == 200

    def test_health_endpoint_returns_healthy_status(self, test_client):
        """Test that health endpoint returns healthy status"""
        response = test_client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "pool" in data

    def test_health_endpoint_includes_pool_stats(self, test_client):
        """Test that health endpoint includes pool statistics"""
        response = test_client.get("/health")
        data = response.json()

        pool = data["pool"]
        assert isinstance(pool, dict)


@pytest.mark.integration
class TestRootEndpoint:
    """Test / (root) endpoint"""

    def test_root_endpoint_returns_200(self, test_client):
        """Test that root endpoint returns 200"""
        response = test_client.get("/")
        assert response.status_code == 200

    def test_root_endpoint_returns_server_info(self, test_client):
        """Test that root endpoint returns server information"""
        response = test_client.get("/")
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    def test_root_endpoint_contains_transport_info(self, test_client):
        """Test that root endpoint includes transport information"""
        response = test_client.get("/")
        data = response.json()

        assert "transport" in data
        assert data["transport"] == "http_streamable"

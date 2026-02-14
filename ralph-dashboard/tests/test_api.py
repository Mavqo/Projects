"""Tests for the FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient

from ralph_dashboard.app import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSystemEndpoints:
    def test_system_status(self, client):
        response = client.get("/api/system/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "version" in data["data"]

    def test_system_metrics(self, client):
        response = client.get("/api/system/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu" in data
        assert "memory" in data
        assert "disk" in data
        assert "gpu" in data

    def test_metrics_history(self, client):
        response = client.get("/api/system/metrics/history?seconds=60")
        assert response.status_code == 200
        data = response.json()
        assert "timestamps" in data
        assert "cpu" in data
        assert "memory" in data


class TestProjectEndpoints:
    def test_list_projects(self, client):
        response = client.get("/api/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_project(self, client):
        response = client.get("/api/projects/nonexistent-project-12345")
        assert response.status_code == 404


class TestConfigEndpoints:
    def test_get_config(self, client):
        response = client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "projects_dir" in data
        assert "refresh_interval_ms" in data


class TestStaticFiles:
    def test_index_page(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Ralph Dashboard" in response.text

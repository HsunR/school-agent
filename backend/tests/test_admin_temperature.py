"""Tests for the temperature endpoint."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_temperature_returns_cpu_and_gpu(monkeypatch, client):
    """Temperature endpoint returns CPU and GPU values from TemperatureMonitor."""
    mock_monitor = MagicMock()
    mock_monitor.get_cpu_temp.return_value = 52.3
    mock_monitor.get_gpu_temp.return_value = 68.0

    import app.api.admin as admin_mod
    admin_mod._temp_monitor = mock_monitor

    resp = client.get("/api/admin/temperature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu_temp"] == 52.3
    assert data["gpu_temp"] == 68.0


def test_temperature_returns_none_when_unavailable(monkeypatch, client):
    """Temperature endpoint returns None when monitor can't read temps."""
    mock_monitor = MagicMock()
    mock_monitor.get_cpu_temp.return_value = None
    mock_monitor.get_gpu_temp.return_value = None

    import app.api.admin as admin_mod
    admin_mod._temp_monitor = mock_monitor

    resp = client.get("/api/admin/temperature")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpu_temp"] is None
    assert data["gpu_temp"] is None

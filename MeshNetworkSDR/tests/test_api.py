"""Tests for Pluto+ SDR REST API and Swagger UI documentation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from pluto_radio.api.app import create_app
from pluto_radio.api.manager import RadioLinkManager


@pytest.fixture
def client() -> TestClient:
    """Create test client fixture with clean manager state."""
    manager = RadioLinkManager()
    manager.stop_link()
    manager.stop_tone()
    app = create_app()
    return TestClient(app)


def test_swagger_docs_ui(client: TestClient) -> None:
    """Verify Swagger UI documentation is accessible at /docs."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_redoc_ui(client: TestClient) -> None:
    """Verify ReDoc documentation is accessible at /redoc."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "redoc" in response.text.lower()


def test_openapi_schema(client: TestClient) -> None:
    """Verify OpenAPI JSON specification schema contains all expected endpoints."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert data["info"]["title"] == "Pluto+ SDR Short-Range IP Radio API"
    paths = data["paths"]
    assert "/health" in paths
    assert "/api/device/info" in paths
    assert "/api/config" in paths
    assert "/api/rf/metrics" in paths
    assert "/api/link/status" in paths
    assert "/api/link/start" in paths
    assert "/api/link/stop" in paths
    assert "/api/link/telemetry" in paths
    assert "/api/network/ping" in paths


def test_root_redirects_to_swagger(client: TestClient) -> None:
    """Verify root URL redirects automatically to Swagger /docs."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_dashboard_endpoint(client: TestClient) -> None:
    """Verify /dashboard returns Mission Control HTML UI."""
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Pluto+ SDR Mesh Mission Control" in response.text
    assert "text/html" in response.headers.get("content-type", "")


def test_health_check_endpoint(client: TestClient) -> None:
    """Verify API health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_device_info_simulation(client: TestClient) -> None:
    """Verify device probe endpoint in simulation mode."""
    response = client.get("/api/device/info?simulation=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SIMULATION"
    assert "PLUTO" in data["model"].upper()


def test_config_get_and_update(client: TestClient) -> None:
    """Verify reading and updating radio configuration."""
    get_res = client.get("/api/config")
    assert get_res.status_code == 200
    cfg = get_res.json()
    assert "radio" in cfg
    assert "center_frequency" in cfg["radio"]

    # Update frequency
    post_res = client.post(
        "/api/config",
        json={"center_frequency": 2402000000, "tx_gain": -2},
    )
    assert post_res.status_code == 200
    update_data = post_res.json()
    assert update_data["status"] == "ok"
    assert update_data["details"]["center_frequency"] == 2402000000
    assert update_data["details"]["tx_gain"] == -2


def test_link_lifecycle_simulation(client: TestClient) -> None:
    """Verify full start, status, telemetry, and stop lifecycle in simulation mode."""
    # Initially idle
    status_res = client.get("/api/link/status")
    assert status_res.status_code == 200
    assert status_res.json()["is_running"] is False

    # Start link in simulation mode
    start_res = client.post(
        "/api/link/start",
        json={
            "ip_cidr": "192.168.30.1/24",
            "peer_ip": "192.168.30.2",
            "freq": 2400000000,
            "fdd": True,
            "simulation": True,
        },
    )
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "ok"

    # Status should now be running
    status_active = client.get("/api/link/status")
    assert status_active.status_code == 200
    assert status_active.json()["is_running"] is True
    assert status_active.json()["node_id"] == 1

    # Telemetry should return stats
    telem_res = client.get("/api/link/telemetry")
    assert telem_res.status_code == 200
    telem = telem_res.json()
    assert "tx_packets" in telem
    assert "rx_packets" in telem
    assert "raw_telemetry_text" in telem

    # Stop link
    stop_res = client.post("/api/link/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "ok"

    # Status should return to idle
    status_stopped = client.get("/api/link/status")
    assert status_stopped.status_code == 200
    assert status_stopped.json()["is_running"] is False

    # Restart link again (verify stop -> restart without resource busy error)
    restart_res = client.post(
        "/api/link/start",
        json={
            "ip_cidr": "192.168.30.1/24",
            "peer_ip": "192.168.30.2",
            "freq": 2400000000,
            "fdd": True,
            "simulation": True,
        },
    )
    assert restart_res.status_code == 200
    assert restart_res.json()["status"] == "ok"

    # Final stop
    stop2_res = client.post("/api/link/stop")
    assert stop2_res.status_code == 200
    assert stop2_res.json()["status"] == "ok"


def test_link_start_with_zero_frequency_overrides(client: TestClient) -> None:
    """Verify that Swagger UI default payload with tx_freq=0 and rx_freq=0 resolves cleanly."""
    res = client.post(
        "/api/link/start",
        json={
            "ip_cidr": "192.168.30.1/24",
            "peer_ip": "192.168.30.2",
            "freq": 2400000000,
            "tx_freq": 0,
            "rx_freq": 0,
            "fdd": True,
            "simulation": True,
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    details = res.json()["details"]
    # Node 1 auto-resolves to base_freq (2.4 GHz) and rx_freq = base + 2 MHz
    assert details["tx_freq"] == 2400000000
    assert details["rx_freq"] == 2402000000

    stop_res = client.post("/api/link/stop")
    assert stop_res.status_code == 200
    assert stop_res.json()["status"] == "ok"

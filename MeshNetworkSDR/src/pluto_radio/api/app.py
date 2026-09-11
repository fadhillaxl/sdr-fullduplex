"""FastAPI Application providing Swagger UI and REST API for Pluto+ SDR IP Radio."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Optional

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from ..hardware.pluto import find_candidate_uris
from .manager import RadioLinkManager
from .schemas import (
    ActionResponse,
    AppConfigSchema,
    ConfigUpdateSchema,
    LinkStatusSchema,
    PlutoDeviceInfoSchema,
    RadioConfigSchema,
    ModulationConfigSchema,
    RFMetricsSchema,
    StartLinkRequest,
    TelemetrySchema,
    PingRequest,
    PingResponse,
    ToneTxRequest,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle handler."""
    logger.info("Pluto+ SDR API server starting up...")
    manager = RadioLinkManager()
    yield
    logger.info("Pluto+ SDR API server shutting down, tearing down any active links...")
    manager.stop_link()
    manager.stop_tone()


def create_app() -> FastAPI:
    """Create and configure FastAPI application with Swagger UI and CORS."""
    app = FastAPI(
        title="Pluto+ SDR Short-Range IP Radio API",
        description="""
# 📡 Pluto+ SDR Short-Range IP Radio REST API & Swagger UI

Backend controller and telemetry interface for the **Pluto+ SDR Direct Short-Range IP Radio**.

### 🌟 Features:
* **Hardware Detection**: Real-time probe of ADALM-Pluto & Pluto+ SDR over USB / IP network (`192.168.2.1`, `192.168.99.240`).
* **RF Spectrum & Telemetry**: Live RSSI, SNR, EVM, CFO, and PAPR measurement.
* **Full-Duplex IP Radio Link (Stage 7)**: Control the Linux TUN/TAP `radio0` interface, BPSK/QPSK modem, and FDD/TDD carrier channels.
* **Live Telemetry & Diagnostics**: Real-time TX/RX packet counters, CRC errors, PER (Packet Error Rate), and throughput.
* **Over-the-Air Ping Verification**: Execute ICMP echo request ping tests between nodes through the RF link.
        """,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Enable CORS for browser access and dashboard frontends
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    manager = RadioLinkManager()

    # -------------------------------------------------------------------------
    # Root & Health Endpoints
    # -------------------------------------------------------------------------
    static_dir = Path(__file__).parent / "static"
    dashboard_file = static_dir / "index.html"

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """Redirect root to Swagger UI documentation."""
        return RedirectResponse(url="/docs")

    @app.get("/dashboard", include_in_schema=False)
    def dashboard() -> Any:
        """Serve real-time Pluto+ SDR Mesh Mission Control Dashboard."""
        if dashboard_file.exists():
            return HTMLResponse(content=dashboard_file.read_text(encoding="utf-8"))
        return RedirectResponse(url="/docs")

    @app.get(
        "/health",
        tags=["System"],
        summary="API Health Check",
        response_model=ActionResponse,
    )
    def health_check() -> ActionResponse:
        """Check API service health."""
        return ActionResponse(
            status="ok",
            message="Pluto+ SDR API service is healthy and running.",
            details={"is_link_running": manager.is_running},
        )

    # -------------------------------------------------------------------------
    # Device & Hardware Endpoints
    # -------------------------------------------------------------------------
    @app.get(
        "/api/device/info",
        tags=["Device"],
        summary="Probe Connected Pluto SDR",
        response_model=PlutoDeviceInfoSchema,
    )
    def get_device_info(
        uri: Optional[str] = Query(default=None, description="Target Pluto URI (e.g. ip:192.168.2.1 or ip:192.168.99.240)"),
        simulation: bool = Query(default=False, description="Run probe in simulation mode"),
    ) -> PlutoDeviceInfoSchema:
        """Probe for connected Pluto SDR hardware via libiio or return simulation status."""
        info = manager.get_device_info(uri=uri, simulation=simulation)
        return PlutoDeviceInfoSchema(
            status=info.status,
            uri=info.uri,
            model=info.model,
            tx_channels=info.tx_channels,
            rx_channels=info.rx_channels,
            sample_rate=info.sample_rate,
            error_message=info.error_message,
            troubleshooting=info.troubleshooting,
        )

    @app.get(
        "/api/device/detect",
        tags=["Device"],
        summary="Scan for Available Pluto SDR Devices",
        response_model=ActionResponse,
    )
    def detect_devices() -> ActionResponse:
        """Scan candidate USB and network IP addresses for Pluto SDRs."""
        candidates = find_candidate_uris()
        info = manager.get_device_info()
        return ActionResponse(
            status="ok",
            message=f"Found {len(candidates)} candidate URI(s). Device status: {info.status}",
            details={
                "candidate_uris": candidates,
                "detected_uri": info.uri,
                "status": info.status,
                "model": info.model,
            },
        )

    # -------------------------------------------------------------------------
    # Configuration Endpoints
    # -------------------------------------------------------------------------
    @app.get(
        "/api/config",
        tags=["Configuration"],
        summary="Get Current Radio Configuration",
        response_model=AppConfigSchema,
    )
    def get_config() -> AppConfigSchema:
        """Fetch current radio, modulation, and network configuration."""
        cfg = manager.config
        return AppConfigSchema(
            radio=RadioConfigSchema(
                uri=cfg.radio.uri,
                center_frequency=cfg.radio.center_frequency,
                sample_rate=cfg.radio.sample_rate,
                bandwidth=cfg.radio.bandwidth,
                tx_gain=cfg.radio.tx_gain,
                rx_gain=cfg.radio.rx_gain,
                rx_gain_mode=cfg.radio.rx_gain_mode,
            ),
            modulation=ModulationConfigSchema(
                mode=cfg.modulation.mode,
            ),
            mtu=cfg.network.mtu,
            simulation_mode=cfg.debug.simulation_mode,
        )

    @app.post(
        "/api/config",
        tags=["Configuration"],
        summary="Update Radio Configuration",
        response_model=ActionResponse,
    )
    def update_config(update: ConfigUpdateSchema) -> ActionResponse:
        """Update active configuration parameters."""
        cfg = manager.config
        if update.center_frequency is not None:
            cfg.radio.center_frequency = update.center_frequency
        if update.sample_rate is not None:
            cfg.radio.sample_rate = update.sample_rate
        if update.bandwidth is not None:
            cfg.radio.bandwidth = update.bandwidth
        if update.tx_gain is not None:
            cfg.radio.tx_gain = update.tx_gain
        if update.rx_gain is not None:
            cfg.radio.rx_gain = update.rx_gain
        if update.uri is not None:
            cfg.radio.uri = update.uri
        if update.modulation is not None:
            cfg.modulation.mode = update.modulation.lower()

        return ActionResponse(
            status="ok",
            message="Configuration updated successfully.",
            details={
                "center_frequency": cfg.radio.center_frequency,
                "sample_rate": cfg.radio.sample_rate,
                "bandwidth": cfg.radio.bandwidth,
                "tx_gain": cfg.radio.tx_gain,
                "rx_gain": cfg.radio.rx_gain,
                "uri": cfg.radio.uri,
                "modulation": cfg.modulation.mode,
            },
        )

    # -------------------------------------------------------------------------
    # RF Spectrum & Tone Endpoints
    # -------------------------------------------------------------------------
    @app.get(
        "/api/rf/metrics",
        tags=["RF & Spectrum"],
        summary="Measure RF Signal Metrics",
        response_model=RFMetricsSchema,
    )
    def measure_rf(
        samples: int = Query(10000, ge=1024, le=65536, description="Number of complex IQ samples to acquire"),
    ) -> RFMetricsSchema:
        """Sample baseband spectrum and compute live RSSI, SNR, EVM, and PAPR."""
        try:
            res = manager.measure_rf(num_samples=samples)
            return RFMetricsSchema(**res)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to measure RF metrics: {e}",
            )

    @app.post(
        "/api/rf/tone",
        tags=["RF & Spectrum"],
        summary="Start Continuous CW Test Tone",
        response_model=ActionResponse,
    )
    def start_test_tone(req: ToneTxRequest) -> ActionResponse:
        """Transmit continuous cyclic complex tone for spectrum analyzer or antenna verification."""
        try:
            manager.start_tone(
                carrier_freq_hz=req.carrier_freq_hz,
                tone_freq_hz=req.tone_freq_hz,
                gain_db=req.gain_db,
                amplitude=req.amplitude,
                uri=req.uri,
                simulation=req.simulation,
            )
            return ActionResponse(
                status="ok",
                message=f"CW test tone active at {req.carrier_freq_hz/1e6:.3f} MHz (+{req.tone_freq_hz/1e3:.1f} kHz offset).",
                details={
                    "carrier_freq_hz": req.carrier_freq_hz,
                    "tone_freq_hz": req.tone_freq_hz,
                    "gain_db": req.gain_db,
                },
            )
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @app.post(
        "/api/rf/stop-tx",
        tags=["RF & Spectrum"],
        summary="Stop RF Transmission",
        response_model=ActionResponse,
    )
    def stop_rf_tx() -> ActionResponse:
        """Stop active continuous test tone transmission."""
        manager.stop_tone()
        return ActionResponse(
            status="ok",
            message="Active RF transmission stopped successfully.",
        )

    # -------------------------------------------------------------------------
    # IP Link Transceiver & Telemetry Endpoints
    # -------------------------------------------------------------------------
    @app.get(
        "/api/link/status",
        tags=["IP Radio Link"],
        summary="Get IP Radio Link Transceiver Status",
        response_model=LinkStatusSchema,
    )
    def get_link_status() -> LinkStatusSchema:
        """Fetch active status of virtual TUN interface and digital modem."""
        status_info = manager.get_link_status()
        return LinkStatusSchema(**status_info)

    @app.post(
        "/api/link/start",
        tags=["IP Radio Link"],
        summary="Start Virtual IP Radio Link (Stage 7)",
        response_model=ActionResponse,
    )
    def start_link(req: StartLinkRequest) -> ActionResponse:
        """Launch the IP Link Transceiver bridging OS TUN interface with Pluto SDR."""
        try:
            res = manager.start_link(
                ip_cidr=req.ip_cidr,
                peer_ip=req.peer_ip,
                freq=req.freq,
                tx_freq=req.tx_freq,
                rx_freq=req.rx_freq,
                fdd=req.fdd,
                tx_gain=req.tx_gain,
                rx_gain=req.rx_gain,
                modulation=req.modulation,
                mtu=req.mtu,
                uri=req.uri,
                simulation=req.simulation,
            )
            return ActionResponse(
                status="ok",
                message=f"IP Radio link active on {res['interface']} ({res['local_ip']} -> {res['peer_ip']})",
                details=res,
            )
        except PermissionError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Root/sudo privileges required to configure virtual TUN network interface.",
            )
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    @app.post(
        "/api/link/stop",
        tags=["IP Radio Link"],
        summary="Stop Virtual IP Radio Link",
        response_model=ActionResponse,
    )
    def stop_link() -> ActionResponse:
        """Stop transceiver threads, release TUN interface, and shut down SDR TX."""
        manager.stop_link()
        return ActionResponse(
            status="ok",
            message="IP Radio link transceiver stopped cleanly.",
        )

    @app.get(
        "/api/link/telemetry",
        tags=["IP Radio Link"],
        summary="Get Real-Time Modem Telemetry & Statistics",
        response_model=TelemetrySchema,
    )
    def get_telemetry() -> TelemetrySchema:
        """Fetch real-time packet statistics, PER, throughput, and RF metrics."""
        data = manager.get_telemetry()
        return TelemetrySchema(**data)

    # -------------------------------------------------------------------------
    # Network Diagnostics & Ping Endpoints
    # -------------------------------------------------------------------------
    @app.post(
        "/api/network/ping",
        tags=["Network Diagnostics"],
        summary="Send ICMP Ping Through SDR Radio Link",
        response_model=PingResponse,
    )
    def execute_ping(req: PingRequest) -> PingResponse:
        """Trigger ICMP ping test over the virtual radio0 interface and parse latency/loss."""
        res = manager.ping_peer(
            target=req.target,
            count=req.count,
            interval=req.interval,
            timeout_sec=req.timeout_sec,
        )
        return PingResponse(**res)

    return app


# Module-level default application instance for uvicorn
app = create_app()

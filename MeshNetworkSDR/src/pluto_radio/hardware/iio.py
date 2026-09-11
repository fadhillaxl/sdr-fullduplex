"""Low-level IIO context discovery and helper utilities."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import iio
    HAS_IIO = True
except Exception as e:
    logger.debug("Failed to import iio (likely libiio/pylibiio version mismatch): %s", e)
    iio = None  # type: ignore
    HAS_IIO = False


def scan_iio_contexts() -> Dict[str, str]:
    """Scan available local and network IIO contexts using pylibiio."""
    if not HAS_IIO:
        logger.warning("pylibiio is not installed or available.")
        return {}

    try:
        if hasattr(iio, "scan_contexts"):
            return iio.scan_contexts() or {}
    except Exception as e:
        logger.debug("Failed to scan IIO contexts: %s", e)
    return {}


import socket


def is_ip_reachable(host: str, ports: tuple[int, ...] = (5337, 80, 22), timeout: float = 0.4) -> bool:
    """Quickly check if the network host is responding on standard Pluto ports (IIOD, HTTP, SSH)."""
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except Exception:
            pass
    return False


def find_candidate_uris(custom_uri: Optional[str] = None) -> List[str]:
    """Return an ordered list of candidate URIs to probe for Pluto SDR."""
    candidates: List[str] = []
    if custom_uri:
        uri_str = custom_uri.strip()
        # If user provides a raw IP or hostname like "192.168.99.240", auto-prefix with "ip:"
        if not any(uri_str.startswith(p) for p in ("ip:", "usb:", "local:", "xml:", "sim:")):
            uri_str = f"ip:{uri_str}"
        candidates.append(uri_str)

    # Add any scanned USB/network contexts
    scanned = scan_iio_contexts()
    for uri in scanned.keys():
        if uri not in candidates:
            candidates.append(uri)

    # Standard fallback URI for ADALM-Pluto default network address
    default_ip = "192.168.2.1"
    cand_uri = f"ip:{default_ip}"
    if cand_uri not in candidates:
        if custom_uri == cand_uri or is_ip_reachable(default_ip):
            candidates.append(cand_uri)

    return candidates


def get_troubleshooting_guide() -> str:
    """Return standard troubleshooting instructions when Pluto is not detected."""
    import sys

    os_tips = ""
    if sys.platform.startswith("win"):
        os_tips = (
            "\nWindows Specific Tips:\n"
            "- Ensure Analog Devices PlutoSDR Windows Driver / libiio Windows is installed.\n"
            "- Check Device Manager under Network Adapters for 'PlutoSDR USB Ethernet/RNDIS Gadget'.\n"
            "- Configure IP: Set IPv4 on the Pluto adapter to 192.168.2.10 (Subnet: 255.255.255.0)."
        )
    elif sys.platform == "darwin":
        os_tips = (
            "\nmacOS Specific Tips:\n"
            "- Check System Settings -> Network for the Pluto USB Ethernet Gadget.\n"
            "- Set IPv4 manually on that interface: IP 192.168.2.10, Subnet Mask 255.255.255.0.\n"
            "- If using USB directly, install libiio via Homebrew: `brew install libiio`."
        )
    else:
        os_tips = (
            "\nLinux Specific Tips:\n"
            "- If 'undefined symbol: iio_get_backends_count' occurs, system libiio is older than pylibiio.\n"
            "  Fix: `sudo apt update && sudo apt install -y libiio-utils libiio-dev python3-libiio`\n"
            "  or in venv: `pip install pylibiio==0.23.1`\n"
            "- Ensure udev rules are installed (/etc/udev/rules.d/53-adi-plutosdr-usb.rules).\n"
            "- Ensure user is member of 'plugdev' or 'dialout': `sudo usermod -a -G plugdev,dialout $USER`."
        )

    return (
        "ERROR: Pluto SDR not detected.\n\n"
        "Check:\n"
        "1. USB connection (ensure cable supports data, not power-only)\n"
        "2. Run `iio_info -s` in your terminal to see connected IIO devices\n"
        "3. Pluto network/USB URI (default is 'ip:192.168.2.1' or 'usb:')\n"
        "4. libiio installation and udev rules (on Linux)\n"
        "5. Permissions (ensure user is in 'plugdev' or 'dialout' group)"
        f"{os_tips}"
    )

"""Cross-Platform Virtual TUN Network Interface (Linux radio0 & macOS utun)."""

from __future__ import annotations

import fcntl
import ipaddress
import logging
import os
import platform
import queue
import socket
import struct
import subprocess
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)

# Linux TUN constants
TUNSETIFF = 0x400454CA
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000

# macOS utun constants
AF_SYSTEM = 32
SYSPROTO_CONTROL = 2
CTLIOCGINFO = 0xC0644E03
UTUN_CONTROL_NAME = b"com.apple.net.utun_control"
UTUN_OPT_IFNAME = 2


class BaseTunDevice(ABC):
    """Abstract base class for virtual network TUN interfaces."""

    def __init__(self, ip_cidr: str, peer_ip: Optional[str] = None, mtu: int = 600):
        self.ip_cidr = ip_cidr
        self.mtu = mtu
        net = ipaddress.IPv4Interface(ip_cidr)
        self.local_ip = str(net.ip)
        self.prefix_len = net.network.prefixlen
        self.netmask = str(net.netmask)

        if peer_ip:
            self.peer_ip = peer_ip
        else:
            # Auto-infer peer in point-to-point /24 link
            octets = self.local_ip.split(".")
            last_byte = int(octets[-1])
            peer_last = 2 if last_byte == 1 else 1
            self.peer_ip = f"{octets[0]}.{octets[1]}.{octets[2]}.{peer_last}"

        self.name: str = "radio0"
        self.is_open: bool = False

    @abstractmethod
    def open(self) -> None:
        """Create, open, and configure the virtual TUN interface."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close and tear down the virtual TUN interface."""
        pass

    @abstractmethod
    def read(self, mtu: int = 1500) -> Optional[bytes]:
        """Read a raw IP packet from the OS network stack."""
        pass

    @abstractmethod
    def write(self, packet: bytes) -> None:
        """Inject a raw IP packet back into the OS network stack."""
        pass


class LinuxTunDevice(BaseTunDevice):
    """Linux TUN driver using /dev/net/tun ioctl (creates 'radio0')."""

    def __init__(self, ip_cidr: str, peer_ip: Optional[str] = None, dev_name: str = "radio0", mtu: int = 600):
        super().__init__(ip_cidr, peer_ip, mtu=mtu)
        self.desired_name = dev_name
        self._fd: Optional[int] = None

    def open(self) -> None:
        tun_path = "/dev/net/tun"
        if not os.path.exists(tun_path):
            raise FileNotFoundError(f"{tun_path} does not exist. Ensure tun kernel module is loaded.")

        self._fd = os.open(tun_path, os.O_RDWR)
        ifr = struct.pack("16sH", self.desired_name.encode("ascii"), IFF_TUN | IFF_NO_PI)
        res = fcntl.ioctl(self._fd, TUNSETIFF, ifr)
        self.name = res[:16].split(b"\x00")[0].decode("ascii")
        self.is_open = True

        # Configure IP address and link state with MTU
        subprocess.run(
            ["ip", "addr", "add", self.ip_cidr, "dev", self.name],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["ip", "link", "set", "dev", self.name, "mtu", str(self.mtu), "up"],
            check=True,
            capture_output=True,
        )
        logger.info("Linux TUN interface %s active with IP %s (MTU %d)", self.name, self.ip_cidr, self.mtu)

    def close(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception:
                pass
            self._fd = None
        self.is_open = False

    def read(self, mtu: int = 1500) -> Optional[bytes]:
        if self._fd is None:
            return None
        try:
            return os.read(self._fd, mtu)
        except (BlockingIOError, InterruptedError):
            return None
        except Exception as e:
            logger.debug("Linux TUN read error: %s", e)
            return None

    def write(self, packet: bytes) -> None:
        if self._fd is None:
            return
        try:
            os.write(self._fd, packet)
        except Exception as e:
            logger.debug("Linux TUN write error: %s", e)


class DarwinUtunDevice(BaseTunDevice):
    """macOS virtual network driver using native BSD PF_SYSTEM utun socket."""

    def __init__(self, ip_cidr: str, peer_ip: Optional[str] = None, mtu: int = 600):
        super().__init__(ip_cidr, peer_ip, mtu=mtu)
        self._sock: Optional[socket.socket] = None

    def open(self) -> None:
        self._sock = socket.socket(AF_SYSTEM, socket.SOCK_DGRAM, SYSPROTO_CONTROL)

        ctl_info = struct.pack("I96s", 0, UTUN_CONTROL_NAME)
        res = fcntl.ioctl(self._sock.fileno(), CTLIOCGINFO, ctl_info)
        ctl_id = struct.unpack("I", res[:4])[0]

        # Connect to allocate dynamic utun unit (unit=0)
        self._sock.connect((ctl_id, 0))

        # Retrieve assigned interface name (e.g. utun3)
        self.name = self._sock.getsockopt(SYSPROTO_CONTROL, UTUN_OPT_IFNAME, 64).decode("utf-8").rstrip("\x00")
        self.is_open = True

        # Configure IP address and bring interface UP on macOS with MTU:
        # ifconfig <utunX> <local_ip> <peer_ip> netmask <netmask> mtu <mtu> up
        cmd = [
            "ifconfig",
            self.name,
            self.local_ip,
            self.peer_ip,
            "netmask",
            self.netmask,
            "mtu",
            str(self.mtu),
            "up",
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Purge any stale routes (e.g. cloned from USB gadget with wide /16 mask) and bind peer_ip and subnet to utun
        try:
            subprocess.run(["route", "delete", "-host", self.peer_ip], capture_output=True)
            subprocess.run(["route", "add", "-host", self.peer_ip, "-interface", self.name], capture_output=True)
            net_cidr = str(ipaddress.IPv4Interface(self.ip_cidr).network)
            subprocess.run(["route", "delete", "-net", net_cidr], capture_output=True)
            subprocess.run(["route", "add", "-net", net_cidr, "-interface", self.name], capture_output=True)
        except Exception as e:
            logger.debug("Failed to configure routes on macOS: %s", e)

        logger.info("macOS utun interface %s active: %s -> %s (MTU %d)", self.name, self.local_ip, self.peer_ip, self.mtu)

    def close(self) -> None:
        try:
            subprocess.run(["route", "delete", "-host", self.peer_ip], capture_output=True)
            net_cidr = str(ipaddress.IPv4Interface(self.ip_cidr).network)
            subprocess.run(["route", "delete", "-net", net_cidr], capture_output=True)
        except Exception:
            pass
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self.is_open = False

    def read(self, mtu: int = 1500) -> Optional[bytes]:
        if self._sock is None:
            return None
        try:
            # macOS utun packets are prefixed with 4-byte AF protocol family
            raw = self._sock.recv(mtu + 4)
            if len(raw) <= 4:
                return None
            return raw[4:]  # Strip 4-byte header to get pure IPv4 packet
        except (BlockingIOError, InterruptedError):
            return None
        except Exception as e:
            logger.debug("Darwin utun read error: %s", e)
            return None

    def write(self, packet: bytes) -> None:
        if self._sock is None:
            return
        try:
            # Inspect first nibble of IP header to determine IP version (4 or 6)
            version = (packet[0] >> 4) if len(packet) > 0 else 4
            family = socket.AF_INET6 if version == 6 else socket.AF_INET
            header = struct.pack("!I", family)
            self._sock.send(header + packet)
        except Exception as e:
            logger.debug("Darwin utun write error: %s", e)


class SimulatedTunDevice(BaseTunDevice):
    """In-memory simulated TUN device for automated testing without root privileges."""

    def __init__(self, ip_cidr: str = "192.168.50.1/24", peer_ip: Optional[str] = None, mtu: int = 600):
        super().__init__(ip_cidr, peer_ip, mtu=mtu)
        self.name = "sim_radio0"
        self.tx_queue: queue.Queue[bytes] = queue.Queue()
        self.rx_queue: queue.Queue[bytes] = queue.Queue()

    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def read(self, mtu: int = 1500) -> Optional[bytes]:
        try:
            return self.tx_queue.get(timeout=0.1)
        except queue.Empty:
            return None

    def write(self, packet: bytes) -> None:
        self.rx_queue.put(packet)

    def inject_tx_packet(self, packet: bytes) -> None:
        """Simulate host network stack sending a packet."""
        self.tx_queue.put(packet)

    def get_received_packet(self, timeout: float = 1.0) -> Optional[bytes]:
        """Fetch packet delivered to simulated network stack."""
        try:
            return self.rx_queue.get(timeout=timeout)
        except queue.Empty:
            return None


def create_tun_device(
    ip_cidr: str,
    peer_ip: Optional[str] = None,
    simulation: bool = False,
    mtu: int = 600,
) -> BaseTunDevice:
    """Factory function to instantiate the correct TUN device for the current platform."""
    if simulation:
        return SimulatedTunDevice(ip_cidr, peer_ip, mtu=mtu)

    os_type = platform.system().lower()
    if os_type == "linux":
        return LinuxTunDevice(ip_cidr, peer_ip, mtu=mtu)
    elif os_type == "darwin":
        return DarwinUtunDevice(ip_cidr, peer_ip, mtu=mtu)
    else:
        # Fallback to simulation mode on unsupported OS (e.g. Windows without TAP)
        logger.warning("Unsupported OS for native kernel TUN: %s. Falling back to simulation.", os_type)
        return SimulatedTunDevice(ip_cidr, peer_ip, mtu=mtu)

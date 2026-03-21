"""
mDNS Advertiser
Registers the FastAPI backend as 'chetan-robot._http._tcp.local.' so that
ESP32 devices can discover it automatically without a hardcoded IP address.
"""

import logging
import socket
import asyncio
from typing import Optional

logger = logging.getLogger(__name__)

# Service constants
MDNS_SERVICE_TYPE = "_http._tcp.local."
MDNS_SERVICE_NAME = "chetan-robot._http._tcp.local."
MDNS_HOSTNAME = "chetan-robot"


def _get_local_ip() -> str:
    """Return the primary non-loopback IPv4 address of this machine."""
    try:
        # Connect to a public address (no data sent) to determine the
        # outbound interface IP.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class MDNSAdvertiser:
    """
    Advertises the backend over mDNS so ESP32 devices can discover it
    using the hostname 'chetan-robot.local' instead of a hardcoded IP.
    """

    def __init__(self, port: int = 8000):
        self._port = port
        self._zeroconf = None
        self._service_info = None
        self._running = False

    def start(self) -> bool:
        """Register mDNS service. Returns True on success."""
        try:
            from zeroconf import ServiceInfo, Zeroconf  # type: ignore
        except ImportError:
            logger.warning(
                "[mDNS] 'zeroconf' package not installed. "
                "Run: pip install zeroconf  — mDNS advertising disabled."
            )
            return False

        local_ip = _get_local_ip()
        logger.info(f"[mDNS] Advertising on {local_ip}:{self._port} as '{MDNS_HOSTNAME}.local'")

        self._service_info = ServiceInfo(
            MDNS_SERVICE_TYPE,
            MDNS_SERVICE_NAME,
            addresses=[socket.inet_aton(local_ip)],
            port=self._port,
            properties={
                "path": "/ws",
                "version": "2.0",
                "device": "chetan-robot-backend",
            },
            server=f"{MDNS_HOSTNAME}.local.",
        )

        try:
            self._zeroconf = Zeroconf()
            self._zeroconf.register_service(self._service_info)
            self._running = True
            logger.info("[mDNS] Service registered successfully")
            return True
        except TimeoutError:
            logger.warning("[mDNS] Registration timed out (Windows/network issue), continuing without mDNS")
            return False
        except Exception as exc:
            logger.warning(f"[mDNS] Registration failed: {exc}, continuing without mDNS")
            return False

    def stop(self) -> None:
        """Unregister mDNS service."""
        if self._zeroconf and self._running:
            try:
                self._zeroconf.unregister_service(self._service_info)
                self._zeroconf.close()
                logger.info("[mDNS] Service unregistered")
            except Exception as exc:
                logger.warning(f"[mDNS] Error during shutdown: {exc}")
            finally:
                self._running = False
                self._zeroconf = None

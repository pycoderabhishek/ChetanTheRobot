"""
UDP Broadcast Discovery Responder
Listens on a UDP port for discovery requests from ESP32 devices and
replies with the backend's IP address and port.

Protocol:
  Request  (ESP32 → broadcast): b"CHETAN_ROBOT_DISCOVERY"
  Response (backend → ESP32):   b"CHETAN_ROBOT_BACKEND:<ip>:<port>"
"""

import asyncio
import logging
import socket

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 54321
DISCOVERY_REQUEST = b"CHETAN_ROBOT_DISCOVERY"
DISCOVERY_RESPONSE_PREFIX = b"CHETAN_ROBOT_BACKEND:"


def _get_local_ip() -> str:
    """Return the primary non-loopback IPv4 address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class UDPBroadcaster:
    """
    Async UDP server that responds to ESP32 discovery broadcasts.
    Start/stop it from FastAPI's lifespan context.
    """

    def __init__(self, port: int = 8000, discovery_port: int = DISCOVERY_PORT):
        self._backend_port = port
        self._discovery_port = discovery_port
        self._transport = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the UDP discovery listener in the background."""
        loop = asyncio.get_event_loop()
        try:
            self._transport, _ = await loop.create_datagram_endpoint(
                lambda: _DiscoveryProtocol(self._backend_port),
                local_addr=("0.0.0.0", self._discovery_port),
                allow_broadcast=True,
            )
            logger.info(
                f"[UDP] Discovery listener started on port {self._discovery_port}"
            )
        except OSError as exc:
            logger.warning(
                f"[UDP] Could not bind discovery port {self._discovery_port}: {exc}. "
                "UDP discovery disabled."
            )

    async def stop(self) -> None:
        """Stop the UDP discovery listener."""
        if self._transport:
            self._transport.close()
            self._transport = None
            logger.info("[UDP] Discovery listener stopped")


class _DiscoveryProtocol(asyncio.DatagramProtocol):
    """asyncio DatagramProtocol that replies to discovery probes."""

    def __init__(self, backend_port: int):
        self._backend_port = backend_port
        self._transport = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple) -> None:
        if data.strip() != DISCOVERY_REQUEST:
            return

        local_ip = _get_local_ip()
        response = DISCOVERY_RESPONSE_PREFIX + f"{local_ip}:{self._backend_port}".encode()
        logger.info(
            f"[UDP] Discovery request from {addr[0]} — responding with {local_ip}:{self._backend_port}"
        )
        self._transport.sendto(response, addr)

    def error_received(self, exc: Exception) -> None:
        logger.warning(f"[UDP] Protocol error: {exc}")

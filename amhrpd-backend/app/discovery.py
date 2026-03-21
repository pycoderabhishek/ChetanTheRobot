"""
Discovery Services for Backend

ESP32 devices can find this backend via:
1. mDNS query: _http._tcp.local
2. UDP broadcast: CHETAN_ROBOT_DISCOVERY
"""

import logging
import socket
import asyncio
from zeroconf import ServiceInfo, Zeroconf

logger = logging.getLogger(__name__)


class MDNSAdvertiser:
    """Advertise backend via mDNS (Layer 1 for ESP32 discovery)"""
    
    def __init__(self, hostname: str = "chetan-robot", port: int = 8000):
        self.hostname = hostname
        self.port = port
        self.zeroconf = None
        self.service_info = None
    
    def _get_local_ip(self) -> str:
        """Get local IP address by connecting to external host"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.warning(f"Could not determine IP: {e}")
            return "127.0.0.1"
    
    def start(self) -> bool:
        """Start mDNS advertisement"""
        try:
            local_ip = self._get_local_ip()
            logger.info(f"[mDNS] Starting mDNS advertiser on {local_ip}:{self.port}")
            
            # Create service info
            self.service_info = ServiceInfo(
                "_http._tcp.local.",
                f"{self.hostname}._http._tcp.local.",
                addresses=[socket.inet_aton(local_ip)],
                port=self.port,
                properties={"path": "/"},
                server=f"{self.hostname}.local."
            )
            
            # Register service
            self.zeroconf = Zeroconf()
            self.zeroconf.register_service(self.service_info)
            
            logger.info(f"[mDNS] ✓ Service advertised: {self.hostname}._http._tcp.local")
            logger.info(f"[mDNS] ✓ ESP32 can now discover backend at {local_ip}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"[mDNS] ✗ Failed to start mDNS: {e}")
            return False
    
    def stop(self):
        """Stop mDNS advertisement"""
        try:
            if self.zeroconf:
                if self.service_info:
                    self.zeroconf.unregister_service(self.service_info)
                self.zeroconf.close()
            logger.info("[mDNS] Stopped")
        except Exception as e:
            logger.error(f"[mDNS] Error stopping: {e}")


class UDPBroadcaster:
    """Advertise backend via UDP broadcast (Layer 2 for ESP32 discovery)"""
    
    def __init__(self, port: int = 8000, udp_port: int = 54321):
        self.port = port
        self.udp_port = udp_port
        self.task = None
        self.running = False
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception as e:
            logger.warning(f"Could not determine IP: {e}")
            return "127.0.0.1"
    
    async def _broadcast_loop(self):
        """Listen for UDP discovery requests and respond with backend info"""
        loop = asyncio.get_event_loop()
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setblocking(False)
        sock.bind(("0.0.0.0", self.udp_port))
        
        logger.info(f"[UDP] Listening for discovery requests on port {self.udp_port}")
        
        while self.running:
            try:
                # Check for incoming messages
                data, addr = await loop.sock_recvfrom(sock, 1024)
                request = data.decode('utf-8', errors='ignore').strip()
                
                if request == "CHETAN_ROBOT_DISCOVERY":
                    local_ip = self._get_local_ip()
                    response = f"CHETAN_ROBOT_BACKEND:{local_ip}:{self.port}"
                    
                    logger.info(f"[UDP] Discovery request from {addr[0]} → responding with {local_ip}:{self.port}")
                    await loop.sock_sendto(sock, response.encode('utf-8'), addr)
            
            except BlockingIOError:
                # No data available yet
                await asyncio.sleep(0.1)
            except Exception as e:
                if self.running:
                    logger.error(f"[UDP] Error: {e}")
                await asyncio.sleep(0.1)
        
        sock.close()
    
    async def start(self):
        """Start UDP broadcast listener"""
        try:
            local_ip = self._get_local_ip()
            self.running = True
            self.task = asyncio.create_task(self._broadcast_loop())
            logger.info(f"[UDP] ✓ Listening on {self.udp_port}")
            logger.info(f"[UDP] ✓ Will respond with backend at {local_ip}:{self.port}")
        except Exception as e:
            logger.error(f"[UDP] ✗ Failed to start: {e}")
    
    async def stop(self):
        """Stop UDP broadcast listener"""
        try:
            self.running = False
            if self.task:
                self.task.cancel()
                try:
                    await self.task
                except asyncio.CancelledError:
                    pass
            logger.info("[UDP] Stopped")
        except Exception as e:
            logger.error(f"[UDP] Error stopping: {e}")

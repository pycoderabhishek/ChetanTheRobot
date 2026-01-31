"""
WebSocket Connection Manager + Command Router
Manages active ESP device connections and command routing

NOTE:
- websocket.accept() MUST be called ONLY in WebSocket endpoint
"""

import asyncio
import uuid
from typing import Dict, List
from fastapi import WebSocket

from app.commands.models import Command
from app.websocket.manager import ConnectionManager


class CommandRouter:
    """Routes commands to appropriate devices via WebSocket"""

    def __init__(self, connection_manager: ConnectionManager, device_registry):
        self.connection_manager = connection_manager
        self.device_registry = device_registry

    async def route_command(
        self,
        device_type: str,
        command_name: str,
        payload: dict = None
    ) -> Command:
        """
        Route a command to all devices of the specified type.
        
        Args:
            device_type: Target device type (e.g., "esp32s3")
            command_name: Name of command (e.g., "resetposition", "handsup")
            payload: Optional payload data
            
        Returns:
            Command object with status
        """
        if payload is None:
            payload = {}

        command_id = str(uuid.uuid4())
        command = Command(
            command_id=command_id,
            device_type=device_type,
            command_name=command_name,
            payload=payload,
            status="pending"
        )

        # Build the message to send
        message = {
            "message_type": "command",
            "command_id": command_id,
            "command_name": command_name,
            "payload": payload
        }

        # Get target devices
        target_devices = await self.device_registry.get_devices_by_type(device_type)
        sent_count = 0

        for device in target_devices:
            if device.is_online:
                success = await self.connection_manager.send_to_device(
                    device.device_id, message
                )
                if success:
                    sent_count += 1

        if sent_count > 0:
            command.status = "sent"
        else:
            command.status = "no_devices"

        return command

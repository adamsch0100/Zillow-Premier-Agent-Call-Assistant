"""
WebSocket connection manager for real-time communication.
"""

from fastapi import WebSocket
from typing import Dict, List, Any
import logging
from enum import Enum
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of messages that can be sent over WebSocket."""
    TRANSCRIPTION = "transcription"
    SUGGESTION = "suggestion"
    ERROR = "error"
    KEEPALIVE = "keepalive"
    STATUS = "status"

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.last_activity: Dict[str, datetime] = {}
        self.cleanup_task: asyncio.Task = None
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Handle new WebSocket connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.last_activity[client_id] = datetime.now()
        logger.info(f"Client {client_id} connected")
        
    async def disconnect(self, client_id: str):
        """Handle WebSocket disconnection."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].close()
            del self.active_connections[client_id]
            del self.last_activity[client_id]
            logger.info(f"Client {client_id} disconnected")
            
    async def send_message(self, message: Dict[str, Any], client_id: str):
        """Send message to specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
                self.last_activity[client_id] = datetime.now()
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {str(e)}")
                await self.disconnect(client_id)
                
    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)
    
    def get_client_status(self, client_id: str) -> Dict:
        """Get status of specific client connection."""
        if client_id in self.active_connections:
            last_active = self.last_activity.get(client_id)
            return {
                "connected": True,
                "last_activity": last_active.isoformat() if last_active else None
            }
        return {"error": "Client not found"}
    
    async def start_cleanup_task(self):
        """Start background task to clean up inactive connections."""
        self.cleanup_task = asyncio.create_task(self._cleanup_inactive_connections())
        
    async def _cleanup_inactive_connections(self):
        """Periodically clean up inactive connections."""
        while True:
            try:
                current_time = datetime.now()
                timeout = timedelta(minutes=30)  # Connection timeout
                
                for client_id in list(self.active_connections.keys()):
                    last_active = self.last_activity.get(client_id)
                    if last_active and (current_time - last_active) > timeout:
                        logger.info(f"Cleaning up inactive connection for client {client_id}")
                        await self.disconnect(client_id)
                        
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute on error

# Create singleton instance
manager = ConnectionManager()
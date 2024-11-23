from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional
import json
import logging
import asyncio
from datetime import datetime
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MessageType(Enum):
    TRANSCRIPTION = "transcription"
    SUGGESTION = "suggestion"
    SYSTEM = "system"
    ERROR = "error"
    KEEPALIVE = "keepalive"

class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class Connection:
    def __init__(self, websocket: WebSocket, client_id: str):
        self.websocket = websocket
        self.client_id = client_id
        self.connected_at = datetime.now()
        self.state = ConnectionState.CONNECTED
        self.message_queue = asyncio.Queue()
        self.last_activity = datetime.now()

    def update_activity(self):
        self.last_activity = datetime.now()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Connection] = {}
        self.message_history: Dict[str, List[dict]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, client_id: str):
        try:
            await websocket.accept()
            connection = Connection(websocket, client_id)
            self.active_connections[client_id] = connection
            self.message_history[client_id] = []
            
            # Start message processing for this connection
            asyncio.create_task(self._process_message_queue(client_id))
            
            logger.info(f"Client {client_id} connected successfully")
            
            # Send welcome message
            await self.send_message(
                {"type": MessageType.SYSTEM.value, "message": "Connected to Real Estate Assistant"},
                client_id
            )
        except Exception as e:
            logger.error(f"Error connecting client {client_id}: {str(e)}")
            raise

    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            self.active_connections[client_id].state = ConnectionState.DISCONNECTED
            del self.active_connections[client_id]
            if client_id in self.message_history:
                del self.message_history[client_id]
            logger.info(f"Client {client_id} disconnected")

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            connection = self.active_connections[client_id]
            await connection.message_queue.put(message)
            connection.update_activity()
        else:
            logger.warning(f"Attempted to send message to non-existent client {client_id}")

    async def broadcast(self, message: dict):
        for client_id in self.active_connections:
            await self.send_message(message, client_id)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

    def get_client_status(self, client_id: str) -> dict:
        if client_id in self.active_connections:
            conn = self.active_connections[client_id]
            return {
                "connected_since": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat(),
                "state": conn.state.value,
                "queued_messages": conn.message_queue.qsize()
            }
        return {"error": "Client not found"}

    async def _process_message_queue(self, client_id: str):
        while client_id in self.active_connections:
            connection = self.active_connections[client_id]
            try:
                message = await connection.message_queue.get()
                await connection.websocket.send_json(message)
                
                # Store message in history (except keepalive)
                if message.get("type") != MessageType.KEEPALIVE.value:
                    self.message_history[client_id].append({
                        "timestamp": datetime.now().isoformat(),
                        "message": message
                    })
                
                connection.message_queue.task_done()
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} websocket disconnected")
                await self.disconnect(client_id)
                break
            except Exception as e:
                logger.error(f"Error processing message for client {client_id}: {str(e)}")
                connection.state = ConnectionState.ERROR
                try:
                    await connection.websocket.send_json({
                        "type": MessageType.ERROR.value,
                        "message": "Error processing message"
                    })
                except:
                    await self.disconnect(client_id)
                    break

    async def start_cleanup_task(self):
        """Start periodic cleanup of inactive connections"""
        async def cleanup():
            while True:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.now()
                for client_id in list(self.active_connections.keys()):
                    conn = self.active_connections[client_id]
                    # Disconnect if inactive for more than 5 minutes
                    if (now - conn.last_activity).seconds > 300:
                        await self.disconnect(client_id)
        
        self._cleanup_task = asyncio.create_task(cleanup())

manager = ConnectionManager()
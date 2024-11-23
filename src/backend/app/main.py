from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Dict, Optional
import json
import uuid
import logging
from datetime import datetime

from core.websocket_manager import manager, MessageType
from services.audio_processor import audio_processor, AudioSegment
from services.suggestion_generator import suggestion_generator, ConversationContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real Estate Call Assistant API",
    description="AI-powered real-time assistant for real estate agents",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store conversation history
conversation_history: Dict[str, List[Dict]] = {}

@app.on_event("startup")
async def startup_event():
    """Initialize the connection manager cleanup task"""
    await manager.start_cleanup_task()

@app.websocket("/ws/call/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, background_tasks: BackgroundTasks):
    try:
        await manager.connect(websocket, client_id)
        conversation_history[client_id] = []
        
        while True:
            try:
                # Receive audio data from the client
                data = await websocket.receive_bytes()
                
                # Process audio through our pipeline
                audio_segment = audio_processor.process_audio_chunk(data)
                
                if audio_segment.is_speech:
                    # Process speech in background task
                    background_tasks.add_task(
                        process_speech,
                        audio_segment,
                        client_id
                    )
                
                # Send periodic keepalive
                await manager.send_message(
                    {"type": MessageType.KEEPALIVE.value},
                    client_id
                )
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for client {client_id}")
                await handle_disconnect(client_id)
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await manager.send_message(
                    {
                        "type": MessageType.ERROR.value,
                        "message": "Error processing audio data"
                    },
                    client_id
                )
                
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {str(e)}")
        await handle_disconnect(client_id)

async def process_speech(audio_segment: AudioSegment, client_id: str):
    """Process speech audio and generate suggestions"""
    try:
        # Transcribe the audio
        transcription_result = await audio_processor.transcribe_audio(audio_segment)
        
        if transcription_result["status"] == "success":
            # Store transcription in conversation history
            conversation_history[client_id].append({
                "text": transcription_result["text"],
                "timestamp": transcription_result["timestamp"],
                "speaker": transcription_result.get("speaker", "unknown")
            })
            
            # Generate context-aware suggestions
            context = ConversationContext(
                transcript="\n".join([msg["text"] for msg in conversation_history[client_id]]),
                last_segment=transcription_result["text"]
            )
            
            suggestions = await suggestion_generator.generate_suggestions(context)
            
            # Send response back to client
            await manager.send_message(
                {
                    "type": MessageType.TRANSCRIPTION.value,
                    "data": {
                        "transcription": transcription_result["text"],
                        "speaker": transcription_result.get("speaker", "unknown"),
                        "timestamp": transcription_result["timestamp"]
                    }
                },
                client_id
            )
            
            # Send suggestions separately
            await manager.send_message(
                {
                    "type": MessageType.SUGGESTION.value,
                    "data": {
                        "suggestions": suggestions,
                        "context": str(context)
                    }
                },
                client_id
            )
    except Exception as e:
        logger.error(f"Error processing speech: {str(e)}")
        await manager.send_message(
            {
                "type": MessageType.ERROR.value,
                "message": "Error processing speech"
            },
            client_id
        )

async def handle_disconnect(client_id: str):
    """Handle client disconnection"""
    await manager.disconnect(client_id)
    if client_id in conversation_history:
        del conversation_history[client_id]

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Real Estate Call Assistant API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": manager.get_connection_count(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/session/new")
async def create_session():
    """Create a new session ID for WebSocket connection"""
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}

@app.get("/api/client/{client_id}/status")
async def get_client_status(client_id: str):
    """Get the status of a specific client connection"""
    status = manager.get_client_status(client_id)
    if "error" in status:
        raise HTTPException(status_code=404, detail="Client not found")
    return status

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    return {
        "active_connections": manager.get_connection_count(),
        "total_conversations": len(conversation_history),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
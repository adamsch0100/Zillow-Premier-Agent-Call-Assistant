"""
WebSocket handler for real-time call processing and suggestions.
"""

import json
import asyncio
import logging
from fastapi import WebSocket
from typing import Dict, Optional
from ..core.conversation_analyzer import ConversationAnalyzer
from ..speech_processing.real_time_processor import RealTimeProcessor

logger = logging.getLogger(__name__)

class CallHandler:
    def __init__(self):
        self.active_calls: Dict[str, Dict] = {}
        self.speech_processor = RealTimeProcessor()
        
    async def connect(self, websocket: WebSocket, call_id: str):
        """Handle new WebSocket connection for a call."""
        await websocket.accept()
        
        self.active_calls[call_id] = {
            'websocket': websocket,
            'analyzer': ConversationAnalyzer(),
            'last_transcript': None,
            'is_processing': False
        }
        
        logger.info(f"New call connection established: {call_id}")
        
        # Send initial state
        await self._send_state(call_id)
        
    async def disconnect(self, call_id: str):
        """Handle WebSocket disconnection."""
        if call_id in self.active_calls:
            # Clean up resources
            self.active_calls[call_id]['is_processing'] = False
            del self.active_calls[call_id]
            logger.info(f"Call disconnected: {call_id}")
            
    async def process_audio(self, call_id: str, audio_data: bytes):
        """Process incoming audio data."""
        if call_id not in self.active_calls:
            logger.error(f"Received audio for unknown call: {call_id}")
            return
            
        call = self.active_calls[call_id]
        if call['is_processing']:
            return  # Skip if still processing previous chunk
            
        call['is_processing'] = True
        try:
            # Process audio and get transcript
            self.speech_processor.process_audio_chunk(
                audio_data,
                lambda text, confidence: asyncio.create_task(
                    self._handle_transcript(call_id, text, confidence)
                )
            )
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
        finally:
            call['is_processing'] = False
            
    async def _handle_transcript(self, call_id: str, text: str, confidence: float):
        """Handle new transcript and generate suggestions."""
        if call_id not in self.active_calls:
            return
            
        call = self.active_calls[call_id]
        
        # Skip if transcript hasn't changed significantly
        if call['last_transcript'] == text:
            return
            
        call['last_transcript'] = text
        
        # Determine if this is agent or client speaking (simplified)
        speaker = self._detect_speaker(text)
        
        # Analyze conversation and get suggestions
        analysis = call['analyzer'].analyze_speech(text, speaker)
        
        # Send update to client
        await self._send_update(call_id, {
            'transcript': text,
            'confidence': confidence,
            'speaker': speaker,
            'suggestions': analysis.get('suggestion', ''),
            'warnings': analysis.get('warnings', []),
            'stage': analysis['stage']
        })
        
    def _detect_speaker(self, text: str) -> str:
        """
        Simple speaker detection based on content.
        In a production system, this would use more sophisticated voice recognition.
        """
        # Simple heuristic: if contains common agent phrases, assume agent
        agent_phrases = [
            "this is", "with realty", "would you like to see",
            "i can show you", "are you available", "excited to work with you"
        ]
        
        return "agent" if any(phrase in text.lower() for phrase in agent_phrases) else "client"
        
    async def _send_update(self, call_id: str, data: Dict):
        """Send update to WebSocket client."""
        if call_id not in self.active_calls:
            return
            
        try:
            await self.active_calls[call_id]['websocket'].send_json(data)
        except Exception as e:
            logger.error(f"Error sending update: {e}")
            await self.disconnect(call_id)
            
    async def _send_state(self, call_id: str):
        """Send current conversation state to client."""
        if call_id not in self.active_calls:
            return
            
        call = self.active_calls[call_id]
        state = {
            'stage': call['analyzer'].state.stage.value,
            'progress': call['analyzer'].get_alm_progress(),
            'last_transcript': call['last_transcript']
        }
        
        try:
            await call['websocket'].send_json({
                'type': 'state',
                'data': state
            })
        except Exception as e:
            logger.error(f"Error sending state: {e}")
            await self.disconnect(call_id)
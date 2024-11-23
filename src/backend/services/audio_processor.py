"""
Audio processing service for real-time speech recognition.
"""

import numpy as np
import speech_recognition as sr
from pydantic import BaseModel
from typing import Dict, Optional
import logging
import asyncio
from datetime import datetime
import webrtcvad
import wave
import io

logger = logging.getLogger(__name__)

class AudioSegment(BaseModel):
    """Model representing a segment of audio data."""
    data: bytes
    is_speech: bool
    timestamp: str
    sample_rate: int = 16000
    
    class Config:
        arbitrary_types_allowed = True

class AudioProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (0-3)
        self.sample_rate = 16000
        self.frame_duration = 30  # ms
        
    def process_audio_chunk(self, audio_data: bytes) -> AudioSegment:
        """
        Process a chunk of audio data.
        
        Args:
            audio_data: Raw audio bytes
            
        Returns:
            AudioSegment object containing processed data and speech detection result
        """
        try:
            # Convert audio data to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Detect speech
            is_speech = self._detect_speech(audio_data)
            
            return AudioSegment(
                data=audio_data,
                is_speech=is_speech,
                timestamp=datetime.now().isoformat(),
                sample_rate=self.sample_rate
            )
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {str(e)}")
            return AudioSegment(
                data=audio_data,
                is_speech=False,
                timestamp=datetime.now().isoformat(),
                sample_rate=self.sample_rate
            )
    
    def _detect_speech(self, audio_data: bytes) -> bool:
        """
        Detect if audio contains speech using WebRTC VAD.
        """
        try:
            # Calculate frame size based on sample rate and frame duration
            frame_size = int(self.sample_rate * self.frame_duration / 1000)
            
            # Process audio in frames
            for i in range(0, len(audio_data), frame_size):
                frame = audio_data[i:i + frame_size]
                if len(frame) == frame_size:  # Only process complete frames
                    if self.vad.is_speech(frame, self.sample_rate):
                        return True
            return False
            
        except Exception as e:
            logger.error(f"Error in speech detection: {str(e)}")
            return False
    
    async def transcribe_audio(self, audio_segment: AudioSegment) -> Dict:
        """
        Transcribe audio data to text.
        
        Args:
            audio_segment: AudioSegment object containing the audio data
            
        Returns:
            Dict containing transcription result
        """
        try:
            if not audio_segment.is_speech:
                return {
                    "status": "no_speech",
                    "text": "",
                    "timestamp": audio_segment.timestamp
                }
            
            # Create AudioData object from raw bytes
            audio_data = sr.AudioData(
                audio_segment.data,
                audio_segment.sample_rate,
                2  # 16-bit audio
            )
            
            # Use Google Speech Recognition
            text = await asyncio.to_thread(
                self.recognizer.recognize_google,
                audio_data,
                language="en-US"
            )
            
            # Detect speaker (simplified version)
            speaker = self._detect_speaker(text)
            
            return {
                "status": "success",
                "text": text,
                "timestamp": audio_segment.timestamp,
                "speaker": speaker
            }
            
        except sr.UnknownValueError:
            return {
                "status": "no_speech",
                "text": "",
                "timestamp": audio_segment.timestamp
            }
        except sr.RequestError as e:
            logger.error(f"Error in speech recognition service: {str(e)}")
            return {
                "status": "error",
                "error": "Speech recognition service error",
                "timestamp": audio_segment.timestamp
            }
        except Exception as e:
            logger.error(f"Error transcribing audio: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": audio_segment.timestamp
            }
    
    def _detect_speaker(self, text: str) -> str:
        """
        Simple speaker detection based on content.
        In a production system, this would use more sophisticated voice recognition.
        """
        # Common phrases used by agents
        agent_phrases = [
            "this is",
            "with realty",
            "would you like to see",
            "i can show you",
            "are you available",
            "excited to work with you",
            "i understand",
            "let me",
            "i would be happy to"
        ]
        
        text = text.lower()
        return "agent" if any(phrase in text for phrase in agent_phrases) else "client"

# Create singleton instance
audio_processor = AudioProcessor()
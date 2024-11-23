import asyncio
from typing import Optional, Dict, List, Tuple
import numpy as np
import webrtcvad
from pydantic import BaseModel
from datetime import datetime
import logging
from scipy import signal
import noisereduce as nr
from collections import deque
import io
import wave
import struct

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioSegment(BaseModel):
    audio_data: bytes
    timestamp: datetime
    speaker_id: Optional[str] = None
    is_speech: bool = False
    confidence: float = 0.0
    noise_level: float = 0.0

class AudioBuffer:
    def __init__(self, max_size: int = 10):
        self.buffer = deque(maxlen=max_size)
        self.total_duration = 0  # in seconds
        
    def add_segment(self, segment: AudioSegment):
        self.buffer.append(segment)
        # Assuming 16kHz sample rate and 16-bit samples
        self.total_duration += len(segment.audio_data) / (16000 * 2)
        
    def get_combined_audio(self) -> bytes:
        return b"".join(segment.audio_data for segment in self.buffer)
    
    def clear(self):
        self.buffer.clear()
        self.total_duration = 0

class SpeakerProfile:
    def __init__(self, speaker_id: str):
        self.speaker_id = speaker_id
        self.audio_samples = []
        self.voice_characteristics = {}

class AudioProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(3)  # Aggressiveness level 3 (highest)
        self.sample_rate = 16000
        self.frame_duration = 30  # ms
        self.buffer = AudioBuffer()
        self.noise_profile = None
        self.speakers: Dict[str, SpeakerProfile] = {
            "agent": SpeakerProfile("agent"),
            "client": SpeakerProfile("client")
        }
        self.current_speaker = None
        self.silence_threshold = 0.1
        self.min_speech_duration = 0.5  # seconds
        
    def _convert_to_mono(self, audio_data: bytes) -> np.ndarray:
        """Convert audio bytes to mono numpy array."""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            if len(audio_array.shape) > 1:
                audio_array = np.mean(audio_array, axis=1)
            return audio_array
        except Exception as e:
            logger.error(f"Error converting audio to mono: {e}")
            raise

    def _reduce_noise(self, audio_array: np.ndarray) -> np.ndarray:
        """Apply noise reduction to audio array."""
        try:
            # Update noise profile from silence periods
            if self.noise_profile is None and not self._detect_speech(audio_array):
                self.noise_profile = audio_array
            
            if self.noise_profile is not None:
                # Apply noise reduction
                reduced = nr.reduce_noise(
                    y=audio_array,
                    sr=self.sample_rate,
                    prop_decrease=0.75,
                    stationary=True
                )
                return reduced
            return audio_array
        except Exception as e:
            logger.error(f"Error reducing noise: {e}")
            return audio_array

    def _detect_speech(self, audio_array: np.ndarray) -> bool:
        """Detect if audio contains speech using energy threshold and VAD."""
        try:
            # Calculate energy
            energy = np.mean(np.abs(audio_array))
            
            # Check if energy is above threshold
            if energy < self.silence_threshold:
                return False
            
            # Convert to proper format for VAD
            audio_bytes = audio_array.astype(np.int16).tobytes()
            frame_length = int(self.sample_rate * self.frame_duration / 1000)
            
            # Use WebRTC VAD for final confirmation
            if len(audio_bytes) >= frame_length:
                return self.vad.is_speech(audio_bytes[:frame_length], self.sample_rate)
            
            return False
        except Exception as e:
            logger.error(f"Error detecting speech: {e}")
            return False

    def _identify_speaker(self, audio_array: np.ndarray) -> Optional[str]:
        """Basic speaker identification using energy and frequency characteristics."""
        try:
            if not self._detect_speech(audio_array):
                return None
                
            # Extract basic voice characteristics
            freqs, times, sx = signal.spectrogram(audio_array, fs=self.sample_rate)
            
            # Simple analysis of frequency distribution
            freq_distribution = np.mean(sx, axis=1)
            peak_freq = freqs[np.argmax(freq_distribution)]
            
            # Basic gender classification based on typical frequency ranges
            # Male voices typically 85-180 Hz, Female voices typically 165-255 Hz
            if peak_freq < 165:
                return "agent"  # Assuming agent is male for this example
            else:
                return "client"  # Assuming client is female for this example
                
        except Exception as e:
            logger.error(f"Error identifying speaker: {e}")
            return None

    def _calculate_noise_level(self, audio_array: np.ndarray) -> float:
        """Calculate the noise level of the audio segment."""
        try:
            # Calculate RMS of the signal
            rms = np.sqrt(np.mean(np.square(audio_array)))
            # Normalize to 0-1 range
            return float(min(1.0, rms / 32768.0))  # 32768 is max value for 16-bit audio
        except Exception as e:
            logger.error(f"Error calculating noise level: {e}")
            return 0.0

    async def process_audio_chunk(self, audio_data: bytes) -> AudioSegment:
        """Process a chunk of audio data with noise reduction and speaker identification."""
        try:
            # Convert to mono numpy array
            audio_array = self._convert_to_mono(audio_data)
            
            # Apply noise reduction
            cleaned_array = self._reduce_noise(audio_array)
            
            # Detect speech
            is_speech = self._detect_speech(cleaned_array)
            
            # Identify speaker if speech is detected
            speaker_id = self._identify_speaker(cleaned_array) if is_speech else None
            
            # Calculate confidence and noise level
            confidence = 1.0 if is_speech else 0.0
            noise_level = self._calculate_noise_level(audio_array)
            
            # Convert back to bytes
            cleaned_audio = cleaned_array.astype(np.int16).tobytes()
            
            # Create segment
            segment = AudioSegment(
                audio_data=cleaned_audio,
                timestamp=datetime.now(),
                speaker_id=speaker_id,
                is_speech=is_speech,
                confidence=confidence,
                noise_level=noise_level
            )
            
            # Add to buffer if speech is detected
            if is_speech:
                self.buffer.add_segment(segment)
            
            return segment
            
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
            return AudioSegment(
                audio_data=audio_data,
                timestamp=datetime.now(),
                is_speech=False,
                confidence=0.0,
                noise_level=1.0
            )

    async def transcribe_audio(self, audio_segment: AudioSegment) -> Dict[str, str]:
        """Transcribe audio using OpenAI's Whisper model with enhanced error handling."""
        if not audio_segment.is_speech:
            return {
                "text": "",
                "status": "no_speech_detected",
                "speaker_id": audio_segment.speaker_id,
                "confidence": 0.0
            }

        try:
            # Only transcribe if we have enough speech data
            if self.buffer.total_duration < self.min_speech_duration:
                return {
                    "text": "",
                    "status": "insufficient_speech_duration",
                    "speaker_id": audio_segment.speaker_id,
                    "confidence": 0.0
                }

            from .openai_service import ai_service, TranscriptionRequest
            
            # Use combined audio from buffer for better context
            combined_audio = self.buffer.get_combined_audio()
            
            request = TranscriptionRequest(
                audio_data=combined_audio,
                timestamp=audio_segment.timestamp,
                language="en"  # You might want to make this configurable
            )
            
            result = await ai_service.transcribe_audio(request)
            
            # Add speaker information to result
            result["speaker_id"] = audio_segment.speaker_id
            
            # Clear buffer after successful transcription
            self.buffer.clear()
            
            return result
            
        except Exception as e:
            logger.error(f"Error in transcription: {e}", exc_info=True)
            return {
                "text": "",
                "status": "error",
                "error": str(e),
                "speaker_id": audio_segment.speaker_id,
                "confidence": 0.0
            }

    def reset(self):
        """Reset the audio processor state."""
        self.buffer.clear()
        self.noise_profile = None
        self.current_speaker = None

audio_processor = AudioProcessor()
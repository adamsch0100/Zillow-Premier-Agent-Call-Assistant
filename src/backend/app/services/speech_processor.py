import numpy as np
import wave
import webrtcvad
import collections
import contextlib
import wave
import struct
from pathlib import Path
from typing import Generator, List, Optional
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class Frame(object):
    """Represents a "frame" of audio data."""
    def __init__(self, bytes: bytes, timestamp: float, duration: float):
        self.bytes = bytes
        self.timestamp = timestamp
        self.duration = duration

class SpeechProcessor:
    def __init__(self):
        self.vad = webrtcvad.Vad(3)  # Aggressiveness mode 3
        self.sample_rate = settings.SAMPLE_RATE
        self.frame_duration_ms = 30  # ms
        self.padding_duration_ms = 300  # ms
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        self.CHUNK = settings.CHUNK_SIZE
        self.triggered = False
        self.ring_buffer = collections.deque(maxlen=self.padding_duration_ms // self.frame_duration_ms)
        
    def frame_generator(self, audio: bytes) -> Generator[Frame, None, None]:
        """Generate audio frames from raw audio data."""
        offset = 0
        timestamp = 0.0
        duration = (float(self.frame_size) / self.sample_rate)
        
        while offset + self.frame_size < len(audio):
            yield Frame(audio[offset:offset + self.frame_size], timestamp, duration)
            timestamp += duration
            offset += self.frame_size

    def process_audio_chunk(self, audio_chunk: bytes) -> Optional[bytes]:
        """Process a chunk of audio data and detect speech segments."""
        if len(audio_chunk) != self.CHUNK * 2:  # 16-bit audio
            return None
            
        # Convert audio chunk to frames
        frames = list(self.frame_generator(audio_chunk))
        if not frames:
            return None
            
        # Process frames for voice activity
        speech_frames = []
        for frame in frames:
            is_speech = self.vad.is_speech(frame.bytes, self.sample_rate)
            
            if not self.triggered:
                self.ring_buffer.append((frame, is_speech))
                num_voiced = len([f for f, speech in self.ring_buffer if speech])
                
                if num_voiced > 0.9 * self.ring_buffer.maxlen:
                    self.triggered = True
                    speech_frames.extend([f.bytes for f, s in self.ring_buffer])
                    self.ring_buffer.clear()
            else:
                speech_frames.append(frame.bytes)
                self.ring_buffer.append((frame, is_speech))
                num_unvoiced = len([f for f, speech in self.ring_buffer if not speech])
                
                if num_unvoiced > 0.9 * self.ring_buffer.maxlen:
                    self.triggered = False
                    self.ring_buffer.clear()
                    
        if speech_frames:
            return b''.join(speech_frames)
        return None

    def save_audio_segment(self, audio_data: bytes, filepath: Path) -> None:
        """Save processed audio segment to a WAV file."""
        with wave.open(str(filepath), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit audio
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)

    @staticmethod
    def normalize_audio(audio_data: bytes) -> bytes:
        """Normalize audio volume."""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Normalize
        normalized = audio_array / np.max(np.abs(audio_array))
        
        # Scale back to 16-bit range
        normalized = (normalized * 32767).astype(np.int16)
        
        return normalized.tobytes()

    def detect_speaker_change(self, audio_data: bytes, prev_audio: Optional[bytes] = None) -> bool:
        """Detect if there's a change in speaker (simple energy-based method)."""
        if prev_audio is None:
            return False
            
        current = np.frombuffer(audio_data, dtype=np.int16)
        previous = np.frombuffer(prev_audio, dtype=np.int16)
        
        # Calculate energy
        current_energy = np.mean(np.abs(current))
        prev_energy = np.mean(np.abs(previous))
        
        # If energy difference is significant, might be speaker change
        return abs(current_energy - prev_energy) > 5000  # Threshold may need tuning

    def get_audio_duration(self, audio_data: bytes) -> float:
        """Calculate duration of audio segment in seconds."""
        return len(audio_data) / (2 * self.sample_rate)  # 2 bytes per sample

    def split_long_audio(self, audio_data: bytes, max_duration: float = 10.0) -> List[bytes]:
        """Split long audio segments into smaller chunks."""
        samples_per_chunk = int(max_duration * self.sample_rate * 2)  # 2 bytes per sample
        return [audio_data[i:i + samples_per_chunk] 
                for i in range(0, len(audio_data), samples_per_chunk)]
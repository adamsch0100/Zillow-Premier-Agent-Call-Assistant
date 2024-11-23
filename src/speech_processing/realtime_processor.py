"""
Real-time speech processing for the Real Estate Call Assistant.
"""

import sounddevice as sd
import numpy as np
import webrtcvad
import wave
import threading
from typing import Callable, Optional
from queue import Queue
import logging

class RealtimeSpeechProcessor:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration: int = 30,
        padding_duration: int = 300,
        speech_callback: Optional[Callable] = None
    ):
        """
        Initialize the real-time speech processor.
        
        Args:
            sample_rate: Audio sample rate in Hz
            frame_duration: Duration of each frame in ms
            padding_duration: Duration of padding around speech in ms
            speech_callback: Callback function for processed speech
        """
        self.sample_rate = sample_rate
        self.frame_duration = frame_duration
        self.padding_duration = padding_duration
        self.speech_callback = speech_callback
        
        # Initialize VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(3)  # Aggressive mode
        
        # Calculate sizes
        self.frame_size = int(sample_rate * frame_duration / 1000)
        self.padding_size = int(sample_rate * padding_duration / 1000)
        
        # Initialize state
        self.audio_queue = Queue()
        self.is_recording = False
        self.current_audio = []
        self.is_speech = False
        self.silence_frames = 0
        
    def start_processing(self):
        """Start processing audio input."""
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_audio)
        self.processing_thread = threading.Thread(target=self._process_audio)
        
        self.recording_thread.start()
        self.processing_thread.start()
        
    def stop_processing(self):
        """Stop processing audio input."""
        self.is_recording = False
        if hasattr(self, 'recording_thread'):
            self.recording_thread.join()
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join()
            
    def _record_audio(self):
        """Record audio from the microphone."""
        try:
            with sd.InputStream(
                channels=1,
                samplerate=self.sample_rate,
                blocksize=self.frame_size,
                dtype=np.int16,
                callback=self._audio_callback
            ):
                while self.is_recording:
                    sd.sleep(100)
        except Exception as e:
            logging.error(f"Error recording audio: {e}")
            self.is_recording = False
            
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio input."""
        if status:
            logging.warning(f"Audio input status: {status}")
        self.audio_queue.put(indata.copy())
        
    def _process_audio(self):
        """Process audio frames for speech detection."""
        while self.is_recording:
            if not self.audio_queue.empty():
                audio_frame = self.audio_queue.get()
                
                # Convert float32 to int16
                audio_frame = (audio_frame * 32768).astype(np.int16)
                
                # Check for speech
                try:
                    is_speech = self.vad.is_speech(
                        audio_frame.tobytes(),
                        self.sample_rate
                    )
                except Exception as e:
                    logging.error(f"Error detecting speech: {e}")
                    continue
                    
                if is_speech:
                    self.is_speech = True
                    self.silence_frames = 0
                    self.current_audio.extend(audio_frame)
                elif self.is_speech:
                    self.silence_frames += 1
                    self.current_audio.extend(audio_frame)
                    
                    # End of speech detected
                    if self.silence_frames > self.padding_duration // self.frame_duration:
                        self._handle_speech_segment()
                        
    def _handle_speech_segment(self):
        """Process a complete speech segment."""
        if self.speech_callback and len(self.current_audio) > 0:
            # Convert to numpy array
            audio_data = np.array(self.current_audio, dtype=np.int16)
            
            # Save to temporary WAV file
            temp_filename = 'temp_speech.wav'
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 2 bytes for int16
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Call the callback with the filename
            self.speech_callback(temp_filename)
        
        # Reset state
        self.current_audio = []
        self.is_speech = False
        self.silence_frames = 0
        
    def set_speech_callback(self, callback: Callable):
        """Set the callback function for processed speech."""
        self.speech_callback = callback
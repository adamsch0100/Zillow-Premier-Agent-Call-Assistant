"""
Real-time speech processing module for the Real Estate Call Assistant.
Handles live audio capture and processing during agent-client calls.
"""

import speech_recognition as sr
from typing import Callable, Optional
import threading
import queue
import logging

class RealTimeProcessor:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.audio_queue = queue.Queue()
        self.is_active = False
        self.callback = None
        self._setup_logging()

    def _setup_logging(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def start_processing(self, callback: Callable[[str, float], None]):
        """
        Start processing audio in real-time.
        
        Args:
            callback: Function to call with transcribed text and confidence score
        """
        self.callback = callback
        self.is_active = True
        self.processing_thread = threading.Thread(target=self._process_audio_queue)
        self.processing_thread.start()
        self._capture_audio()

    def stop_processing(self):
        """Stop all audio processing."""
        self.is_active = False
        self.audio_queue.put(None)  # Signal to stop processing
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join()

    def _capture_audio(self):
        """Capture audio from microphone and add to processing queue."""
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source)
            self.logger.info("Started audio capture")
            
            while self.is_active:
                try:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=10)
                    self.audio_queue.put(audio)
                except sr.WaitTimeoutError:
                    continue
                except Exception as e:
                    self.logger.error(f"Error capturing audio: {e}")

    def _process_audio_queue(self):
        """Process audio segments from the queue."""
        while self.is_active:
            audio = self.audio_queue.get()
            if audio is None:
                break

            try:
                text = self.recognizer.recognize_google(audio)
                confidence = 0.9  # Placeholder until we implement confidence scoring
                if self.callback:
                    self.callback(text, confidence)
            except sr.UnknownValueError:
                self.logger.debug("Could not understand audio")
            except sr.RequestError as e:
                self.logger.error(f"Error with speech recognition service: {e}")
            except Exception as e:
                self.logger.error(f"Unexpected error processing audio: {e}")
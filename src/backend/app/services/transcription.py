import os
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import numpy as np
from typing import Dict, Optional, Tuple
import logging
from pathlib import Path
import time
from ..core.config import settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.device = torch.device(settings.DEVICE)
        self.processor = None
        self.model = None
        self.last_speaker = None
        self.silence_threshold = float(os.getenv('SILENCE_THRESHOLD', 500)) / 1000  # Convert ms to seconds
        self.last_transcription_time = 0
        self.use_openai = os.getenv('USE_OPENAI_WHISPER', 'true').lower() == 'true'
        if not self.use_openai:
            self.initialize_model()

    def initialize_model(self) -> None:
        """Initialize the Whisper model for transcription."""
        try:
            logger.info("Loading Whisper model...")
            self.processor = WhisperProcessor.from_pretrained("openai/whisper-base")
            self.model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-base")
            self.model.to(self.device)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {str(e)}")
            raise

    def preprocess_audio(self, audio_data: bytes) -> torch.Tensor:
        """Convert raw audio bytes to model input format."""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
        
        # Normalize
        audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Convert to tensor
        input_features = self.processor(
            audio_array,
            sampling_rate=settings.SAMPLE_RATE,
            return_tensors="pt"
        ).input_features
        
        return input_features.to(self.device)

    async def transcribe_audio(
        self,
        audio_data: bytes,
        speaker_hint: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio segment and return structured result.
        
        Args:
            audio_data: Raw audio bytes
            speaker_hint: Optional hint about who is speaking ('agent' or 'customer')
            
        Returns:
            Dictionary containing transcription results
        """
        try:
            # Check if enough time has passed since last transcription
            current_time = time.time()
            if current_time - self.last_transcription_time < self.silence_threshold:
                return None
            
            if self.use_openai:
                # Use OpenAI's Whisper API
                from .openai_service import ai_service, TranscriptionRequest
                
                request = TranscriptionRequest(
                    audio_data=audio_data,
                    timestamp=current_time,
                    language="en"
                )
                
                result = await ai_service.transcribe_audio(request)
                
                if result and result.get("status") == "success":
                    transcription = result["text"]
                    confidence = result.get("confidence", 1.0)
                else:
                    logger.warning("OpenAI transcription failed, falling back to local model")
                    if not self.model:
                        self.initialize_model()
                    # Fallback to local model
                    input_features = self.preprocess_audio(audio_data)
                    generated_ids = self.model.generate(input_features)
                    transcription = self.processor.batch_decode(
                        generated_ids,
                        skip_special_tokens=True
                    )[0]
                    confidence = self.calculate_confidence(generated_ids)
            else:
                # Use local model
                input_features = self.preprocess_audio(audio_data)
                generated_ids = self.model.generate(input_features)
                transcription = self.processor.batch_decode(
                    generated_ids,
                    skip_special_tokens=True
                )[0]
                confidence = self.calculate_confidence(generated_ids)
            
            # Determine speaker
            speaker = self.determine_speaker(speaker_hint)
            self.last_speaker = speaker
            
            # Update last transcription time
            self.last_transcription_time = current_time
            
            # Clean and enhance the transcription
            transcription = self.clean_transcription(transcription)
            
            result = {
                "text": transcription.strip(),
                "speaker": speaker,
                "timestamp": current_time,
                "confidence": confidence
            }
            
            # Enhance with additional information
            return self.enhance_transcription(result)
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return None

    def determine_speaker(self, speaker_hint: Optional[str]) -> str:
        """Determine who is speaking based on hints and context."""
        if speaker_hint:
            return speaker_hint
            
        # If no hint, alternate between speakers
        if self.last_speaker == "agent":
            return "customer"
        return "agent"

    def calculate_confidence(self, generated_ids: torch.Tensor) -> float:
        """Calculate confidence score for transcription."""
        # Simple confidence calculation based on model logits
        with torch.no_grad():
            logits = self.model.get_logits(generated_ids)
            probs = torch.softmax(logits, dim=-1)
            confidence = torch.mean(torch.max(probs, dim=-1)[0]).item()
        return confidence

    def validate_transcription(self, transcription: Dict) -> bool:
        """Validate transcription results."""
        if not transcription or not transcription["text"]:
            return False
            
        # Check minimum confidence
        if transcription["confidence"] < 0.6:  # Configurable threshold
            return False
            
        # Check for minimum length
        if len(transcription["text"].split()) < 2:
            return False
            
        return True

    def enhance_transcription(self, transcription: Dict) -> Dict:
        """Enhance transcription with additional information."""
        if not transcription:
            return transcription
            
        # Add metadata
        transcription["word_count"] = len(transcription["text"].split())
        transcription["duration"] = time.time() - transcription["timestamp"]
        
        # Clean up text
        transcription["text"] = self.clean_transcription(transcription["text"])
        
        return transcription

    @staticmethod
    def clean_transcription(text: str) -> str:
        """Clean up transcribed text."""
        # Remove multiple spaces
        text = " ".join(text.split())
        
        # Capitalize first letter of sentences
        text = ". ".join(s.capitalize() for s in text.split(". "))
        
        # Remove common speech artifacts
        artifacts = ["um", "uh", "ah", "er"]
        for artifact in artifacts:
            text = text.replace(f" {artifact} ", " ")
        
        return text.strip()

    def reset(self) -> None:
        """Reset service state between calls."""
        self.last_speaker = None
        self.last_transcription_time = 0
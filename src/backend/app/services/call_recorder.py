import os
from datetime import datetime
import wave
import json
from typing import Optional, Dict, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class CallRecorder:
    def __init__(self):
        self.base_path = Path("/home/computeruse/real-estate-assistant/data/recordings")
        self.current_recording: Optional[Dict] = None
        self.ensure_directories()
        self.load_recording_history()

    def ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.base_path,
            self.base_path / "calls",
            self.base_path / "metadata"
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def start_recording(self, client_id: str, agent_id: str) -> Dict:
        """Start a new call recording session."""
        timestamp = datetime.now()
        recording_id = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{client_id}"
        
        self.current_recording = {
            "recording_id": recording_id,
            "client_id": client_id,
            "agent_id": agent_id,
            "start_time": timestamp.isoformat(),
            "end_time": None,
            "duration": 0,
            "file_path": str(self.base_path / "calls" / f"{recording_id}.wav"),
            "metadata_path": str(self.base_path / "metadata" / f"{recording_id}.json"),
            "status": "recording"
        }
        
        # Initialize WAV file
        with wave.open(self.current_recording["file_path"], 'wb') as wf:
            wf.setnchannels(1)  # Mono
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(16000)  # 16kHz
        
        self._save_metadata()
        return self.current_recording

    def add_audio_chunk(self, audio_data: bytes) -> None:
        """Add an audio chunk to the current recording."""
        if not self.current_recording or self.current_recording["status"] != "recording":
            raise RuntimeError("No active recording session")
        
        with wave.open(self.current_recording["file_path"], 'ab') as wf:
            wf.writeframes(audio_data)

    def stop_recording(self) -> Dict:
        """Stop the current recording and save metadata."""
        if not self.current_recording:
            raise RuntimeError("No active recording session")
        
        end_time = datetime.now()
        self.current_recording.update({
            "end_time": end_time.isoformat(),
            "status": "completed",
            "duration": (end_time - datetime.fromisoformat(self.current_recording["start_time"])).total_seconds()
        })
        
        self._save_metadata()
        self._update_recording_history()
        
        completed_recording = self.current_recording
        self.current_recording = None
        return completed_recording

    def _save_metadata(self) -> None:
        """Save metadata for the current recording."""
        if self.current_recording:
            with open(self.current_recording["metadata_path"], 'w') as f:
                json.dump(self.current_recording, f, indent=2)

    def _update_recording_history(self) -> None:
        """Update the recording history file."""
        history_file = self.base_path / "recording_history.json"
        history = []
        
        if history_file.exists():
            with open(history_file, 'r') as f:
                history = json.load(f)
        
        history.append(self.current_recording)
        
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def load_recording_history(self) -> List[Dict]:
        """Load the recording history."""
        history_file = self.base_path / "recording_history.json"
        if history_file.exists():
            with open(history_file, 'r') as f:
                return json.load(f)
        return []

    def get_recording_info(self, recording_id: str) -> Optional[Dict]:
        """Get information about a specific recording."""
        metadata_path = self.base_path / "metadata" / f"{recording_id}.json"
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                return json.load(f)
        return None

call_recorder = CallRecorder()
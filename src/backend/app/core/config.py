from pydantic import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    # Base
    PROJECT_NAME: str = "Real Estate Call Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    AUDIO_DIR: Path = BASE_DIR / "data" / "audio"
    TRANSCRIPTS_DIR: Path = BASE_DIR / "data" / "transcripts"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    WORKERS: int = 1
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Speech Recognition
    SAMPLE_RATE: int = 16000
    CHANNELS: int = 1
    CHUNK_SIZE: int = 1024
    FORMAT: str = "wav"
    
    # WebSocket
    WS_PING_INTERVAL: int = 20  # seconds
    WS_PING_TIMEOUT: int = 60  # seconds
    
    # Response Matching
    RESPONSE_CONFIDENCE_THRESHOLD: float = 0.7
    MAX_SUGGESTIONS: int = 3
    
    # MLOps
    MODEL_CACHE_DIR: Path = BASE_DIR / "models" / "cache"
    DEVICE: str = "cuda" if os.getenv("USE_GPU", "0") == "1" else "cpu"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
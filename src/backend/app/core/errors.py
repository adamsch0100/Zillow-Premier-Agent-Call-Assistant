from typing import Optional, Dict, Any
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Base exception for AI service errors."""
    def __init__(self, message: str, error_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        logger.error(f"{error_type}: {message} - Details: {details}")

class TranscriptionError(AIServiceError):
    """Raised when there's an error in audio transcription."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TRANSCRIPTION_ERROR", details)

class SuggestionError(AIServiceError):
    """Raised when there's an error in generating suggestions."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SUGGESTION_ERROR", details)

class RateLimitError(AIServiceError):
    """Raised when hitting API rate limits."""
    def __init__(self, message: str, retry_after: int, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details['retry_after'] = retry_after
        super().__init__(message, "RATE_LIMIT_ERROR", details)

class APIKeyError(AIServiceError):
    """Raised when there are issues with the API key."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "API_KEY_ERROR", details)

class ModelError(AIServiceError):
    """Raised when there are issues with the AI model."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "MODEL_ERROR", details)

def handle_openai_error(error: Exception) -> AIServiceError:
    """Convert OpenAI exceptions to our custom error types."""
    import openai

    error_msg = str(error)
    
    if isinstance(error, openai.RateLimitError):
        # Extract retry after value from error message if available
        retry_after = 60  # Default to 60 seconds
        return RateLimitError(
            "Rate limit exceeded",
            retry_after=retry_after,
            details={'original_error': error_msg}
        )
    
    elif isinstance(error, openai.AuthenticationError):
        return APIKeyError(
            "Invalid API key",
            details={'original_error': error_msg}
        )
        
    elif isinstance(error, openai.APIError):
        return ModelError(
            "API error occurred",
            details={'original_error': error_msg}
        )
        
    # Generic error handler
    return AIServiceError(
        "An unexpected error occurred",
        "UNKNOWN_ERROR",
        details={'original_error': error_msg}
    )
from typing import Optional, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAssistantError(Exception):
    """Base exception class for AI Assistant errors."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

        # Log the error
        logger.error(f"{self.__class__.__name__}: {self.message}")
        if self.details:
            logger.error(f"Error details: {self.details}")

class OpenAIServiceError(AIAssistantError):
    """Exception raised for errors in the OpenAI service."""
    pass

class TranscriptionError(OpenAIServiceError):
    """Exception raised for errors during audio transcription."""
    pass

class SuggestionGenerationError(OpenAIServiceError):
    """Exception raised for errors during suggestion generation."""
    pass

class ConversationAnalysisError(OpenAIServiceError):
    """Exception raised for errors during conversation analysis."""
    pass

class AudioProcessingError(AIAssistantError):
    """Exception raised for errors during audio processing."""
    pass

class ValidationError(AIAssistantError):
    """Exception raised for validation errors."""
    pass

class EnvironmentError(AIAssistantError):
    """Exception raised for environment configuration errors."""
    pass

class DatabaseError(AIAssistantError):
    """Exception raised for database-related errors."""
    pass

def handle_openai_error(error: Exception) -> OpenAIServiceError:
    """Convert OpenAI API errors to our custom error types."""
    import openai

    error_mapping = {
        openai.APIError: (OpenAIServiceError, "OpenAI API error occurred"),
        openai.APIConnectionError: (OpenAIServiceError, "Failed to connect to OpenAI API"),
        openai.RateLimitError: (OpenAIServiceError, "Rate limit exceeded"),
        openai.AuthenticationError: (OpenAIServiceError, "Authentication failed"),
        openai.PermissionError: (OpenAIServiceError, "Permission denied"),
        openai.InvalidRequestError: (OpenAIServiceError, "Invalid request"),
        openai.InternalServerError: (OpenAIServiceError, "OpenAI internal server error"),
    }

    error_class, default_message = error_mapping.get(
        type(error),
        (OpenAIServiceError, "Unexpected OpenAI service error")
    )

    details = {
        "error_type": type(error).__name__,
        "original_error": str(error)
    }

    if hasattr(error, "response"):
        details["response"] = error.response

    return error_class(
        message=str(error) or default_message,
        details=details
    )

def check_environment_variables() -> None:
    """Check if all required environment variables are set and validate their values."""
    import os
    from typing import Dict, Any, Optional
    
    required_vars: Dict[str, Optional[Dict[str, Any]]] = {
        "OPENAI_API_KEY": {
            "validator": lambda x: len(x) > 20 and x.startswith("sk-"),
            "error": "Invalid OpenAI API key format"
        },
        "DEBUG": {
            "validator": lambda x: x.lower() in ["true", "false"],
            "error": "DEBUG must be 'true' or 'false'"
        },
        "LOG_LEVEL": {
            "validator": lambda x: x.upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            "error": "Invalid LOG_LEVEL value"
        },
        "MAX_RETRIES": {
            "validator": lambda x: x.isdigit() and 1 <= int(x) <= 5,
            "error": "MAX_RETRIES must be between 1 and 5"
        },
        "RETRY_DELAY": {
            "validator": lambda x: x.isdigit() and 1 <= int(x) <= 30,
            "error": "RETRY_DELAY must be between 1 and 30 seconds"
        }
    }

    # Check for missing variables
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(
            message="Missing required environment variables",
            details={"missing_variables": missing_vars}
        )
    
    # Validate variable values
    validation_errors = {}
    for var, config in required_vars.items():
        if config and "validator" in config:
            value = os.getenv(var)
            try:
                if not config["validator"](value):
                    validation_errors[var] = config["error"]
            except Exception:
                validation_errors[var] = config["error"]
    
    if validation_errors:
        raise EnvironmentError(
            message="Invalid environment variable values",
            details={"validation_errors": validation_errors}
        )

def handle_validation_error(data: Dict[str, Any], error: Exception) -> ValidationError:
    """Handle validation errors for request data."""
    return ValidationError(
        message="Invalid request data",
        details={
            "error": str(error),
            "data": data
        }
    )
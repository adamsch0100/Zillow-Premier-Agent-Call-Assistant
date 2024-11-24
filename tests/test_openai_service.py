import pytest
import os
from datetime import datetime
from unittest.mock import Mock, patch
import json

from src.backend.app.services.openai_service import AIService, TranscriptionRequest, SuggestionRequest
from src.backend.app.core.errors import TranscriptionError, SuggestionError, RateLimitError

# Test data
SAMPLE_AUDIO = b'dummy_audio_data'
SAMPLE_TRANSCRIPT = "Hi, I'm interested in viewing the property."
SAMPLE_CONVERSATION = [
    {"speaker": "customer", "text": "Hi, I'm interested in viewing the property."},
    {"speaker": "agent", "text": "Great! I'd be happy to help you with that."}
]

@pytest.fixture
def ai_service():
    """Create an instance of AIService for testing."""
    return AIService()

@pytest.fixture
def transcription_request():
    """Create a sample TranscriptionRequest."""
    return TranscriptionRequest(
        audio_data=SAMPLE_AUDIO,
        timestamp=datetime.now(),
        language="en"
    )

@pytest.fixture
def suggestion_request():
    """Create a sample SuggestionRequest."""
    return SuggestionRequest(
        transcript=SAMPLE_TRANSCRIPT,
        conversation_history=SAMPLE_CONVERSATION,
        current_stage="initial"
    )

@pytest.mark.asyncio
async def test_transcribe_audio_success(ai_service, transcription_request):
    """Test successful audio transcription."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_response.text = "Hello, I'd like to view the property"
        mock_response.confidence = 0.95
        
        mock_openai.return_value.audio.transcriptions.create.return_value = mock_response
        
        result = await ai_service.transcribe_audio(transcription_request)
        
        assert result["status"] == "success"
        assert isinstance(result["text"], str)
        assert result["confidence"] >= 0.9
        assert "timestamp" in result

@pytest.mark.asyncio
async def test_transcribe_audio_rate_limit(ai_service, transcription_request):
    """Test handling of rate limit errors."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_openai.return_value.audio.transcriptions.create.side_effect = RateLimitError(
            "Rate limit exceeded",
            60,
            {"retry_after": 60}
        )
        
        with pytest.raises(RateLimitError) as exc_info:
            await ai_service.transcribe_audio(transcription_request)
        
        assert exc_info.value.error_type == "RATE_LIMIT_ERROR"
        assert exc_info.value.details.get("retry_after") == 60

@pytest.mark.asyncio
async def test_generate_suggestions_success(ai_service, suggestion_request):
    """Test successful suggestion generation."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Would you like to schedule a viewing?"
        mock_choice.message.content_filter_results = {"confidence": 0.95}
        mock_response.choices = [mock_choice]
        
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        suggestions = await ai_service.generate_suggestions(suggestion_request)
        
        assert len(suggestions) > 0
        assert isinstance(suggestions[0]["text"], str)
        assert suggestions[0]["confidence"] > 0.9
        assert "type" in suggestions[0]

@pytest.mark.asyncio
async def test_generate_suggestions_fallback(ai_service, suggestion_request):
    """Test fallback suggestion generation when API fails."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
        
        suggestions = await ai_service.generate_suggestions(suggestion_request)
        
        assert len(suggestions) > 0
        assert all(s["type"] == "fallback" for s in suggestions)
        assert all(isinstance(s["text"], str) for s in suggestions)

@pytest.mark.asyncio
async def test_analyze_conversation_success(ai_service):
    """Test successful conversation analysis."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = json.dumps({
            "stage": "initial",
            "objections": [],
            "interest_level": "high",
            "needs": ["viewing"],
            "topics": ["property viewing"],
            "next_actions": ["schedule appointment"]
        })
        mock_response.choices = [mock_choice]
        
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        result = await ai_service.analyze_conversation(SAMPLE_TRANSCRIPT)
        
        assert result["status"] == "success"
        assert "stage" in result
        assert "interest_level" in result
        assert "timestamp" in result

@pytest.mark.asyncio
async def test_analyze_conversation_error(ai_service):
    """Test error handling in conversation analysis."""
    with patch('openai.AsyncOpenAI') as mock_openai:
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")
        
        result = await ai_service.analyze_conversation(SAMPLE_TRANSCRIPT)
        
        assert result["status"] == "error"
        assert result["stage"] == "unknown"
        assert isinstance(result["error"], str)
        assert "timestamp" in result
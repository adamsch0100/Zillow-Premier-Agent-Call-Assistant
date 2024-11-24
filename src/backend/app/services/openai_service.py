import openai
from openai import AsyncOpenAI
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import asyncio
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from ..errors import (
    check_environment_variables,
    handle_openai_error,
    handle_validation_error,
    TranscriptionError,
    SuggestionGenerationError,
    ConversationAnalysisError
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables and validate them
load_dotenv()
check_environment_variables()

# Initialize AsyncOpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_rate_limit(rate_limiter):
    """Helper function to check rate limits and raise appropriate errors."""
    if not rate_limiter.can_make_request():
        wait_time = rate_limiter.time_until_available()
        raise AIAssistantError(
            message="Rate limit exceeded",
            details={
                "retry_after": wait_time,
                "error_type": "rate_limit",
                "max_requests": rate_limiter.max_requests,
                "time_window": rate_limiter.time_window
            }
        )

def validate_openai_response(response, error_class, required_fields=None):
    """Helper function to validate OpenAI API responses."""
    if not response.choices or not response.choices[0].message.content:
        raise error_class(
            message="Empty or invalid response from OpenAI",
            details={"response": response}
        )
    
    content = response.choices[0].message.content
    
    if required_fields:
        try:
            parsed = json.loads(content)
            missing_fields = [field for field in required_fields if field not in parsed]
            if missing_fields:
                raise error_class(
                    message="Incomplete response",
                    details={"missing_fields": missing_fields}
                )
            return parsed
        except json.JSONDecodeError as e:
            raise error_class(
                message="Failed to parse response",
                details={"error": str(e), "content": content}
            )
    
    return content

def format_error_details(error, **additional_details):
    """Helper function to format error details consistently."""
    return {
        "error": str(error),
        "error_type": type(error).__name__,
        "timestamp": datetime.utcnow().isoformat(),
        **additional_details
    }

def secure_temp_file_handling(operation):
    """Decorator for secure temporary file operations."""
    async def wrapper(*args, **kwargs):
        temp_file = None
        try:
            temp_file = f"/tmp/audio_chunks/chunk_{int(datetime.now().timestamp())}_{os.getpid()}.wav"
            os.makedirs("/tmp/audio_chunks", exist_ok=True)
            result = await operation(*args, temp_file=temp_file, **kwargs)
            return result
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    # Securely wipe file contents before deletion
                    with open(temp_file, 'wb') as f:
                        f.write(b'0' * os.path.getsize(temp_file))
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(
                        "Failed to clean up temporary file",
                        extra={"file_path": temp_file, "error": str(e)}
                    )
    return wrapper

from pydantic import Field, validator
from datetime import timedelta
import time
from typing import ClassVar

class RateLimiter:
    """Rate limiter implementation for API calls."""
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window  # in seconds
        self.requests = []
    
    def can_make_request(self) -> bool:
        current_time = time.time()
        # Remove old requests
        self.requests = [t for t in self.requests if current_time - t < self.time_window]
        return len(self.requests) < self.max_requests
    
    def add_request(self):
        self.requests.append(time.time())
    
    def time_until_available(self) -> float:
        if self.can_make_request():
            return 0
        current_time = time.time()
        oldest_request = min(self.requests)
        return self.time_window - (current_time - oldest_request)

class TranscriptionRequest(BaseModel):
    audio_data: bytes = Field(..., description="Raw audio data to be transcribed")
    timestamp: datetime = Field(..., description="Timestamp when the audio was recorded")
    language: str = Field(
        default="en",
        regex="^[a-z]{2}(-[A-Z]{2})?$",
        description="Language code in ISO format (e.g., 'en' or 'en-US')"
    )
    voice_metrics: Optional[Dict] = Field(
        default=None,
        description="Optional voice analysis metrics"
    )

    # Static rate limiter for all transcription requests
    _rate_limiter: ClassVar[RateLimiter] = RateLimiter(max_requests=50, time_window=60)

    @validator('audio_data')
    def validate_audio_data(cls, v):
        if len(v) == 0:
            raise ValueError("Audio data cannot be empty")
        if len(v) > 25 * 1024 * 1024:  # 25MB limit
            raise ValueError("Audio data exceeds maximum size of 25MB")
        return v

    @validator('timestamp')
    def validate_timestamp(cls, v):
        now = datetime.utcnow()
        if v > now + timedelta(seconds=5):
            raise ValueError("Timestamp cannot be in the future")
        if v < now - timedelta(hours=24):
            raise ValueError("Timestamp too old (max 24 hours)")
        return v

class SuggestionRequest(BaseModel):
    transcript: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The transcript text to generate suggestions for"
    )
    conversation_history: List[Dict[str, str]] = Field(
        ...,
        max_items=50,
        description="List of previous conversation messages"
    )
    current_stage: str = Field(
        ...,
        regex="^(initial|qualification|objection|closing)$",
        description="Current stage of the conversation"
    )
    identified_objections: List[str] = Field(
        default=[],
        max_items=10,
        description="List of identified client objections"
    )
    client_needs: List[str] = Field(
        default=[],
        max_items=10,
        description="List of identified client needs"
    )
    interest_level: str = Field(
        default="unknown",
        regex="^(unknown|low|medium|high)$",
        description="Client's assessed interest level"
    )
    property_details: Dict[str, str] = Field(
        default={},
        description="Details about the property being discussed"
    )
    agent_info: Dict[str, str] = Field(
        default={},
        description="Information about the agent"
    )
    market_insights: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Market data and insights"
    )
    voice_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Voice analysis metrics"
    )
    conversation_dynamics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Conversation flow and dynamics metrics"
    )

    # Static rate limiter for all suggestion requests (more generous than transcription)
    _rate_limiter: ClassVar[RateLimiter] = RateLimiter(max_requests=100, time_window=60)
    
    @validator('conversation_history')
    def validate_conversation_history(cls, v):
        if not v:
            raise ValueError("Conversation history cannot be empty")
        
        required_keys = {"speaker", "text"}
        for msg in v:
            if not isinstance(msg, dict):
                raise ValueError("Each conversation history item must be a dictionary")
            if not required_keys.issubset(msg.keys()):
                raise ValueError(f"Each message must contain keys: {required_keys}")
            if msg["speaker"] not in {"agent", "client", "system"}:
                raise ValueError("Speaker must be 'agent', 'client', or 'system'")
        return v

    @validator('property_details')
    def validate_property_details(cls, v):
        required_keys = {"address", "price", "type"}
        if v and not all(key in v for key in required_keys):
            raise ValueError(f"Property details must contain keys: {required_keys}")
        return v

    @validator('agent_info')
    def validate_agent_info(cls, v):
        required_keys = {"name", "experience"}
        if v and not all(key in v for key in required_keys):
            raise ValueError(f"Agent info must contain keys: {required_keys}")
        return v

class AIService:
    def __init__(self):
        self.system_prompt = """You are an AI assistant for real estate agents handling Zillow Premier Agent leads.
        Your PRIMARY goal is to help agents secure appointments following the ALM Framework:

        A: APPOINTMENT (FIRST PRIORITY)
        - Secure the appointment as early as possible in the conversation
        - This is your primary objective
        - Use questions like:
          * "Great, when would you like to go see the property?"
          * "Would tomorrow or the next day work better for viewing?"
          * If property unavailable: "When would you like to see other similar homes?"

        L: LOCATION (SECOND PRIORITY)
        - After securing appointment, understand location preferences
        - Aim to show multiple properties
        - Use questions like:
          * "Are there any other properties you've been looking at?"
          * "Are you only interested in this area, or are you open to seeing alternative locations?"

        M: MOTIVATION (THIRD PRIORITY)
        - Only after appointment and location are addressed
        - Understand what drew them to the property
        - Use questions like:
          * "What interests you about this property?"
          * "How long have you been looking?"

        CRITICAL RULES:
        1. ALWAYS prioritize setting the appointment first
        2. Do not get sidetracked with property details before securing appointment
        3. Keep responses focused on moving toward the appointment
        4. Other details can be discussed during showing
        5. Follow ALM order strictly: Appointment → Location → Motivation

        Remember:
        - The appointment is ALWAYS the primary goal
        - Don't discuss extensive property details until appointment is secured
        - Keep responses concise and focused on next steps
        - Move conversation toward appointment quickly and professionally"""
        
        self.max_retries = 3
        self.request_timeout = 30

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    @secure_temp_file_handling
    async def transcribe_audio(self, request: TranscriptionRequest, temp_file: str) -> Dict:
        """
        Transcribe audio using OpenAI's Whisper model with enhanced error handling and retry logic.
        Includes rate limiting and improved input validation.
        """
        try:
            # Check rate limit using helper
            check_rate_limit(request._rate_limiter)
            
            # Track this request for rate limiting
            request._rate_limiter.add_request()

            # Write audio data to temp file with secure permissions
            try:
                with open(temp_file, "wb") as f:
                    f.write(request.audio_data)
                os.chmod(temp_file, 0o600)  # Restrictive permissions
            except IOError as e:
                raise AudioProcessingError(
                    message="Failed to save audio data",
                    details=format_error_details(e, file_path=temp_file)
                )

            # Process audio with OpenAI Whisper
            try:
                async with asyncio.timeout(self.request_timeout):
                    with open(temp_file, "rb") as audio_file:
                        transcription = await client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-1",
                            language=request.language,
                            response_format="verbose_json",
                            temperature=0.0  # More accurate transcriptions
                        )
            except asyncio.TimeoutError:
                raise TranscriptionError(
                    message=f"Transcription request timed out after {self.request_timeout} seconds",
                    details=format_error_details(None, timeout_value=self.request_timeout)
                )
            except openai.OpenAIError as e:
                raise handle_openai_error(e)
            except Exception as e:
                raise TranscriptionError(
                    message="Failed to transcribe audio",
                    details=format_error_details(e, audio_size=len(request.audio_data))
                )

            # Validate transcription result
            if not hasattr(transcription, 'text'):
                raise TranscriptionError(
                    message="Invalid transcription response format",
                    details={"response_type": type(transcription).__name__}
                )
            
            text = transcription.text.strip()
            if not text:
                raise TranscriptionError(
                    message="Empty transcription result",
                    details={
                        "transcription": transcription,
                        "audio_size": len(request.audio_data)
                    }
                )

            # Build enhanced response with metrics
            response = {
                "text": text,
                "status": "success",
                "timestamp": request.timestamp.isoformat(),
                "confidence": getattr(transcription, "confidence", 1.0),
                "language": getattr(transcription, "language", request.language),
                "metadata": {
                    "model": "whisper-1",
                    "audio_size": len(request.audio_data),
                    "processing_time": time.time() - request.timestamp.timestamp(),
                    "word_count": len(text.split()),
                }
            }

            # Add voice metrics if available
            if request.voice_metrics:
                response["voice_analysis"] = request.voice_metrics

            return response

        except AIAssistantError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors during response processing
            raise TranscriptionError(
                message="Error processing transcription result",
                details=format_error_details(e)
            )
                # Use secure file operations
                with open(temp_file, "wb") as f:
                    f.write(request.audio_data)
                os.chmod(temp_file, 0o600)  # Restrictive permissions
            except IOError as e:
                raise AudioProcessingError(
                    message="Failed to save audio data",
                    details={
                        "error": str(e),
                        "error_type": "io_error",
                        "file_path": temp_file
                    }
                )

            try:
                # Track this request for rate limiting
                request._rate_limiter.add_request()
                
                # Use OpenAI's Whisper model with async client
                async with asyncio.timeout(self.request_timeout):
                    with open(temp_file, "rb") as audio_file:
                        transcription = await client.audio.transcriptions.create(
                            file=audio_file,
                            model="whisper-1",
                            language=request.language,
                            response_format="verbose_json",
                            temperature=0.0  # More accurate transcriptions
                        )

            except asyncio.TimeoutError:
                raise TranscriptionError(
                    message=f"Transcription request timed out after {self.request_timeout} seconds",
                    details={
                        "error_type": "timeout",
                        "timeout_value": self.request_timeout,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            except openai.OpenAIError as e:
                error = handle_openai_error(e)
                # Log additional context
                logger.error(
                    "OpenAI transcription error",
                    extra={
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                        "language": request.language,
                        "audio_size": len(request.audio_data)
                    }
                )
                raise error
            except Exception as e:
                raise TranscriptionError(
                    message="Failed to transcribe audio",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            try:
                # Validate transcription result more thoroughly
                if not hasattr(transcription, 'text'):
                    raise TranscriptionError(
                        message="Invalid transcription response format",
                        details={"response_type": type(transcription).__name__}
                    )
                
                text = transcription.text.strip()
                if not text:
                    raise TranscriptionError(
                        message="Empty transcription result",
                        details={
                            "transcription": transcription,
                            "audio_size": len(request.audio_data)
                        }
                    )

                # Build enhanced response with metrics
                response = {
                    "text": text,
                    "status": "success",
                    "timestamp": request.timestamp.isoformat(),
                    "confidence": getattr(transcription, "confidence", 1.0),
                    "language": getattr(transcription, "language", request.language),
                    "metadata": {
                        "model": "whisper-1",
                        "audio_size": len(request.audio_data),
                        "processing_time": time.time() - request.timestamp.timestamp(),
                        "word_count": len(text.split()),
                    }
                }

                # Add voice metrics if available
                if request.voice_metrics:
                    response["voice_analysis"] = request.voice_metrics

                return response

            except AIAssistantError:
                # Re-raise our custom exceptions
                raise

            except Exception as e:
                # Catch any unexpected errors during response processing
                raise TranscriptionError(
                    message="Error processing transcription result",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        finally:
            # Secure cleanup of temporary files
            if temp_file:
                try:
                    if os.path.exists(temp_file):
                        # Securely wipe file contents before deletion
                        with open(temp_file, 'wb') as f:
                            f.write(b'0' * os.path.getsize(temp_file))
                        os.remove(temp_file)
                except Exception as e:
                    logger.warning(
                        "Failed to clean up temporary file",
                        extra={
                            "file_path": temp_file,
                            "error": str(e),
                            "error_type": type(e).__name__
                        }
                    )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_suggestions(self, request: SuggestionRequest) -> List[Dict[str, Any]]:
        """
        Generate context-aware suggestions using GPT-4 with enhanced error handling,
        rate limiting, and comprehensive response validation.
        """
        try:
            # Check rate limit
            if not request._rate_limiter.can_make_request():
                wait_time = request._rate_limiter.time_until_available()
                raise AIAssistantError(
                    message="Rate limit exceeded for suggestion generation",
                    details={
                        "retry_after": wait_time,
                        "error_type": "rate_limit",
                        "max_requests": request._rate_limiter.max_requests,
                        "time_window": request._rate_limiter.time_window
                    }
                )

            # Track this request for rate limiting
            request._rate_limiter.add_request()

            # Format conversation history with more context
            try:
                conversation_context = self._format_conversation_history(request.conversation_history)
            except Exception as e:
                raise ValidationError(
                    message="Invalid conversation history format",
                    details={"error": str(e), "history": request.conversation_history}
                )

            # Build contexts with error handling
            try:
                contexts = self._build_request_contexts(request)
            except Exception as e:
                raise ValidationError(
                    message="Error formatting context data",
                    details={"error": str(e)}
                )

            # Build prompt with all available context
            prompt = self._build_suggestion_prompt(
                conversation_context=conversation_context,
                current_stage=request.current_stage,
                interest_level=request.interest_level,
                identified_objections=request.identified_objections,
                client_needs=request.client_needs,
                **contexts
            )

            try:
                # Get suggestions from GPT-4 with timeout protection
                async with asyncio.timeout(self.request_timeout):
                    response = await client.chat.completions.create(
                        model="gpt-4-1106-preview",
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7,
                        max_tokens=200,
                        n=3,
                        presence_penalty=0.6,  # Encourage diverse responses
                        frequency_penalty=0.3  # Reduce repetition
                    )

            except asyncio.TimeoutError:
                raise SuggestionGenerationError(
                    message=f"Suggestion generation timed out after {self.request_timeout} seconds",
                    details={
                        "error_type": "timeout",
                        "timeout_value": self.request_timeout,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
            except openai.OpenAIError as e:
                error = handle_openai_error(e)
                logger.error(
                    "OpenAI suggestion generation error",
                    extra={
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat(),
                        "stage": request.current_stage
                    }
                )
                raise error
            except Exception as e:
                raise SuggestionGenerationError(
                    message="Failed to generate suggestions",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

            # Process and validate suggestions
            try:
                suggestions = self._process_suggestion_response(response, request)
                if not suggestions:
                    raise SuggestionGenerationError(
                        message="No valid suggestions generated",
                        details={"response": response}
                    )
                return suggestions

            except AIAssistantError:
                raise
            except Exception as e:
                raise SuggestionGenerationError(
                    message="Error processing suggestions",
                    details={
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )

        except AIAssistantError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating suggestions: {str(e)}")
            return self._get_fallback_suggestions(request)

    def _format_conversation_history(self, history: List[Dict[str, str]]) -> str:
        """Format conversation history into a string with proper context."""
        return "\n".join([
            f"{msg['speaker'].title()}: {msg['text']}"
            for msg in history[-10:]  # Last 10 messages
        ])

    def _build_request_contexts(self, request: SuggestionRequest) -> Dict[str, str]:
        """Build all context strings from request data."""
        contexts = {}
        
        if request.property_details:
            contexts['property_context'] = "Property Details:\n" + "\n".join([
                f"- {key.title()}: {value}"
                for key, value in request.property_details.items()
            ])

        if request.agent_info:
            contexts['agent_context'] = "Agent Information:\n" + "\n".join([
                f"- {key.title()}: {value}"
                for key, value in request.agent_info.items()
            ])

        if request.voice_metrics:
            emotion_scores = request.voice_metrics.get('emotion_scores', {})
            contexts['emotional_context'] = f"""
Client Voice Analysis:
- Confidence Level: {emotion_scores.get('confident', 0):.2f}
- Interest Level: {emotion_scores.get('interested', 0):.2f}
- Hesitation Level: {emotion_scores.get('hesitant', 0):.2f}
- Speaking Rate: {request.voice_metrics.get('speaking_rate', 0):.1f} words/min
- Overall Sentiment: {'Positive' if emotion_scores.get('positive', 0) > 0.5 else 'Negative'}"""

        if request.market_insights:
            contexts['market_context'] = f"""
Market Insights:
- Median Price: ${request.market_insights.get('median_price', 0):,.0f}
- Days on Market: {request.market_insights.get('days_on_market', 0)} days
- Market Status: {request.market_insights.get('market_status', 'unknown')}
- Price Trend: {request.market_insights.get('price_trend', 0):+.1f}%
- Similar Listings: {request.market_insights.get('similar_listings', 0)}"""

        if request.conversation_dynamics:
            contexts['dynamics_context'] = f"""
Conversation Dynamics:
- Turn Balance: {request.conversation_dynamics.get('turn_taking_balance', 0):.2f}
- Engagement Score: {request.conversation_dynamics.get('engagement_score', 0):.2f}
- Interruption Count: {request.conversation_dynamics.get('interruption_count', 0)}
- Silence Ratio: {request.conversation_dynamics.get('silence_ratio', 0):.2f}"""

        return contexts

    def _build_suggestion_prompt(self, conversation_context: str, **kwargs) -> str:
        """Build the complete prompt for suggestion generation."""
        # Base prompt with conversation context
        prompt = f"Based on this real estate lead conversation:\n\n{conversation_context}\n\n"
        
        # Add basic context
        prompt += f"""Context:
- Current stage: {kwargs.get('current_stage')}
- Interest level: {kwargs.get('interest_level')}
- Identified objections: {', '.join(kwargs.get('identified_objections', [])) or 'None'}
- Client needs: {', '.join(kwargs.get('client_needs', [])) or 'Not yet identified'}\n\n"""
        
        # Add optional contexts
        for context_key in ['property_context', 'agent_context', 'emotional_context', 
                          'market_context', 'dynamics_context']:
            if context_key in kwargs and kwargs[context_key]:
                prompt += f"{kwargs[context_key]}\n\n"
        
        # Add generation instructions
        prompt += """Generate 3 strategic responses that:
1. Match the client's emotional state and engagement level
2. Use market insights appropriately to build urgency and trust
3. Address objections with both emotional and logical responses
4. Move naturally toward setting an appointment
5. Consider the conversation dynamics and adjust approach accordingly
6. Stay concise and conversational while demonstrating market expertise

Format each suggestion as a brief, ready-to-use response.
Return ONLY the suggested responses, one per line, without numbering or additional formatting."""
        
        return prompt

    def _process_suggestion_response(
        self, 
        response: Any, 
        request: SuggestionRequest
    ) -> List[Dict[str, Any]]:
        """Process and validate the GPT response into structured suggestions."""
        if not response.choices:
            raise SuggestionGenerationError(
                message="Empty response from GPT",
                details={"response": response}
            )

        suggestions = []
        for choice in response.choices:
            suggestion_text = choice.message.content.strip()
            if not suggestion_text:
                continue

            # Validate suggestion length
            if len(suggestion_text) > 200:  # Maximum length for a suggestion
                suggestion_text = suggestion_text[:197] + "..."

            suggestion = {
                "text": suggestion_text,
                "confidence": float(choice.message.content_filter_results.get("confidence", 1.0)),
                "type": "dynamic",
                "metadata": {
                    "stage": request.current_stage,
                    "interest_level": request.interest_level,
                    "addressed_objections": [
                        obj for obj in request.identified_objections
                        if obj.lower() in suggestion_text.lower()
                    ],
                    "length": len(suggestion_text),
                    "word_count": len(suggestion_text.split()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }

            # Add emotional context if available
            if request.voice_metrics and 'emotion_scores' in request.voice_metrics:
                suggestion["metadata"]["emotion_match"] = {
                    "confidence": request.voice_metrics['emotion_scores'].get('confident', 0),
                    "interest": request.voice_metrics['emotion_scores'].get('interested', 0)
                }

            suggestions.append(suggestion)

        return suggestions
                ])
            except (KeyError, TypeError) as e:
                raise ValidationError(
                    message="Invalid conversation history format",
                    details={"error": str(e), "history": request.conversation_history}
                )

            # Build contexts with error handling
            try:
                # Create property context
                property_context = ""
                if request.property_details:
                    property_context = "Property Details:\n" + "\n".join([
                        f"- {key}: {value}"
                        for key, value in request.property_details.items()
                    ])

                # Create agent context
                agent_context = ""
                if request.agent_info:
                    agent_context = "Agent Information:\n" + "\n".join([
                        f"- {key}: {value}"
                        for key, value in request.agent_info.items()
                    ])

                # Create emotional context from voice metrics
                emotional_context = ""
                if request.voice_metrics:
                    emotion_scores = request.voice_metrics.get('emotion_scores', {})
                    emotional_context = f"""
Client Voice Analysis:
- Confidence Level: {emotion_scores.get('confident', 0):.2f}
- Interest Level: {emotion_scores.get('interested', 0):.2f}
- Hesitation Level: {emotion_scores.get('hesitant', 0):.2f}
- Speaking Rate: {request.voice_metrics.get('speaking_rate', 0):.1f} words/min
- Overall Sentiment: {'Positive' if emotion_scores.get('positive', 0) > 0.5 else 'Negative'}"""

                # Create market context from insights
                market_context = ""
                if request.market_insights:
                    market_context = f"""
Market Insights:
- Median Price: ${request.market_insights.get('median_price', 0):,.0f}
- Days on Market: {request.market_insights.get('days_on_market', 0)} days
- Market Status: {request.market_insights.get('market_status', 'unknown')}
- Price Trend: {request.market_insights.get('price_trend', 0):+.1f}%
- Similar Listings: {request.market_insights.get('similar_listings', 0)}"""

                # Create conversation dynamics context
                dynamics_context = ""
                if request.conversation_dynamics:
                    dynamics_context = f"""
Conversation Dynamics:
- Turn Balance: {request.conversation_dynamics.get('turn_taking_balance', 0):.2f}
- Engagement Score: {request.conversation_dynamics.get('engagement_score', 0):.2f}
- Interruption Count: {request.conversation_dynamics.get('interruption_count', 0)}
- Silence Ratio: {request.conversation_dynamics.get('silence_ratio', 0):.2f}"""

            except Exception as e:
                raise ValidationError(
                    message="Error formatting context data",
                    details={"error": str(e)}
                )

            # Build prompt
            prompt = f"""Based on this real estate lead conversation:

{conversation_context}

Context:
- Current stage: {request.current_stage}
- Interest level: {request.interest_level}
- Identified objections: {', '.join(request.identified_objections) if request.identified_objections else 'None'}
- Client needs: {', '.join(request.client_needs) if request.client_needs else 'Not yet identified'}

{property_context if property_context else ''}

{agent_context if agent_context else ''}

{emotional_context if request.voice_metrics else ''}

{market_context if request.market_insights else ''}

{dynamics_context if request.conversation_dynamics else ''}

Generate 3 strategic responses that:
1. Match the client's emotional state and engagement level
2. Use market insights appropriately to build urgency and trust
3. Address objections with both emotional and logical responses
4. Move naturally toward setting an appointment
5. Consider the conversation dynamics and adjust approach accordingly
6. Stay concise and conversational while demonstrating market expertise

Guidelines:
- If client shows hesitation (>0.6), focus on building trust with market data
- If interest is high (>0.7), move more directly toward scheduling
- Match speaking pace to client's comfort level
- Use market insights strategically to overcome objections
- Address any negative sentiment with empathy and data
- If engagement is low, use questions to increase interaction

Guidelines:
- Keep responses concise and actionable
- Focus on building rapport and trust
- Use proper real estate terminology
- Adapt tone based on client's interest level
- Address specific needs and objections when possible
- Avoid discussing detailed financials early
- Guide toward in-person viewing when appropriate

Format each suggestion as a brief, ready-to-use response.
Return ONLY the suggested responses, one per line, without numbering or additional formatting."""

            try:
                # Get suggestions from GPT-4
                response = await client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=200,
                    n=3
                )
            except openai.OpenAIError as e:
                raise handle_openai_error(e)
            except Exception as e:
                raise SuggestionGenerationError(
                    message="Failed to generate suggestions",
                    details={"error": str(e)}
                )

            # Validate and process response
            if not response.choices:
                raise SuggestionGenerationError(
                    message="No suggestions generated",
                    details={"response": response}
                )

            # Process and format suggestions
            try:
                suggestions = []
                for choice in response.choices:
                    suggestion_text = choice.message.content.strip()
                    if not suggestion_text:
                        continue

                    suggestions.append({
                        "text": suggestion_text,
                        "confidence": float(choice.message.content_filter_results.get("confidence", 1.0)),
                        "type": "dynamic",
                        "context": {
                            "stage": request.current_stage,
                            "interest_level": request.interest_level,
                            "addressed_objections": [
                                obj for obj in request.identified_objections
                                if obj.lower() in suggestion_text.lower()
                            ]
                        }
                    })

                if not suggestions:
                    raise SuggestionGenerationError(
                        message="All generated suggestions were empty",
                        details={"choices": response.choices}
                    )

                return suggestions

            except Exception as e:
                raise SuggestionGenerationError(
                    message="Error processing suggestions",
                    details={"error": str(e)}
                )

        except AIAssistantError:
            # Re-raise our custom exceptions
            raise

        except Exception as e:
            # For any unexpected errors, fall back to default suggestions
            logger.error(f"Unexpected error generating suggestions: {str(e)}")
            return self._get_fallback_suggestions(request)

    def _get_fallback_suggestions(self, request: SuggestionRequest) -> List[Dict[str, str]]:
        """
        Provide context-aware fallback suggestions when the main suggestion generation fails.
        """
        stage = request.current_stage.lower()
        fallbacks = []

        if stage == "initial":
            fallbacks = [
                "Would you like to tell me more about what you're looking for in a home?",
                "What's your timeline for making a move?",
                "Have you had a chance to view any properties in person yet?"
            ]
        elif stage == "qualification":
            fallbacks = [
                "What features are most important to you in your next home?",
                "Would you be interested in scheduling a viewing of some properties that match your criteria?",
                "What areas are you most interested in?"
            ]
        elif stage == "objection":
            fallbacks = [
                "I understand your concerns. Would it help if we discussed this in person?",
                "What specific aspects are you most concerned about?",
                "Let's schedule a time to meet and address all your questions in detail."
            ]
        else:  # closing or unknown
            fallbacks = [
                "Would you be interested in scheduling a viewing?",
                "What would be the best time for us to meet and discuss your options?",
                "I'd love to show you some properties that match your criteria. When works best for you?"
            ]

        return [{"text": text, "confidence": 0.8, "type": "fallback"} for text in fallbacks]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_conversation(self, transcript: str) -> Dict:
        """
        Analyze conversation to detect stage and objections with enhanced error handling and retry logic.
        """
        try:
            # Validate input
            if not transcript or not isinstance(transcript, str):
                raise ValidationError(
                    message="Invalid transcript provided",
                    details={"transcript_type": type(transcript).__name__}
                )

            if len(transcript.strip()) < 10:  # Arbitrary minimum length
                raise ValidationError(
                    message="Transcript too short for meaningful analysis",
                    details={"transcript_length": len(transcript)}
                )

            # Prepare analysis prompt
            prompt = f"""Analyze this real estate lead call transcript:

{transcript}

Identify:
1. The conversation stage (initial, qualification, objection, closing)
2. Any objections raised by the prospect
3. The prospect's apparent level of interest (high, medium, low)
4. Any specific needs or preferences mentioned
5. Key topics discussed
6. Next best actions

Format the response as JSON with these keys: stage, objections, interest_level, needs, topics, next_actions"""

            try:
                # Get analysis from GPT-4
                response = await client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=200,
                    response_format={ "type": "json_object" }
                )
            except openai.OpenAIError as e:
                raise handle_openai_error(e)
            except Exception as e:
                raise ConversationAnalysisError(
                    message="Failed to analyze conversation",
                    details={"error": str(e)}
                )

            # Validate response
            if not response.choices or not response.choices[0].message.content:
                raise ConversationAnalysisError(
                    message="No analysis generated",
                    details={"response": response}
                )

            try:
                # Parse and validate JSON response
                analysis = json.loads(response.choices[0].message.content)
                
                # Validate required fields
                required_fields = ['stage', 'objections', 'interest_level', 'needs', 'topics', 'next_actions']
                missing_fields = [field for field in required_fields if field not in analysis]
                
                if missing_fields:
                    raise ConversationAnalysisError(
                        message="Incomplete analysis response",
                        details={"missing_fields": missing_fields}
                    )

                # Validate field types
                if not isinstance(analysis['objections'], list):
                    analysis['objections'] = []
                if not isinstance(analysis['needs'], list):
                    analysis['needs'] = []
                if not isinstance(analysis['topics'], list):
                    analysis['topics'] = []
                if not isinstance(analysis['next_actions'], list):
                    analysis['next_actions'] = []

                # Validate stage value
                valid_stages = {'initial', 'qualification', 'objection', 'closing'}
                if analysis['stage'] not in valid_stages:
                    analysis['stage'] = 'unknown'

                # Validate interest level
                valid_interest_levels = {'high', 'medium', 'low'}
                if analysis['interest_level'] not in valid_interest_levels:
                    analysis['interest_level'] = 'unknown'

                return {
                    "status": "success",
                    **analysis,
                    "timestamp": datetime.now().isoformat()
                }

            except json.JSONDecodeError as e:
                raise ConversationAnalysisError(
                    message="Failed to parse analysis response",
                    details={
                        "error": str(e),
                        "content": response.choices[0].message.content
                    }
                )
            except Exception as e:
                raise ConversationAnalysisError(
                    message="Error processing analysis results",
                    details={"error": str(e)}
                )

        except AIAssistantError as e:
            # Log the error and return a fallback response
            logger.error(f"Analysis error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "stage": "unknown",
                "objections": [],
                "interest_level": "unknown",
                "needs": [],
                "topics": [],
                "next_actions": ["Retry analysis"],
                "timestamp": datetime.now().isoformat(),
                "error_details": e.details
            }

        except Exception as e:
            # Handle any unexpected errors
            logger.error(f"Unexpected error during analysis: {str(e)}")
            return {
                "status": "error",
                "error": "Unexpected error during analysis",
                "stage": "unknown",
                "objections": [],
                "interest_level": "unknown",
                "needs": [],
                "topics": [],
                "next_actions": ["Retry analysis"],
                "timestamp": datetime.now().isoformat()
            }

ai_service = AIService()
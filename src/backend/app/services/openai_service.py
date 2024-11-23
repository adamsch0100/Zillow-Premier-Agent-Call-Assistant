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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize AsyncOpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class TranscriptionRequest(BaseModel):
    audio_data: bytes
    timestamp: datetime
    language: str = "en"
    voice_metrics: Optional[Dict] = None

class SuggestionRequest(BaseModel):
    transcript: str
    conversation_history: List[Dict[str, str]]
    current_stage: str
    identified_objections: List[str] = []
    client_needs: List[str] = []
    interest_level: str = "unknown"
    property_details: Dict[str, str] = {}
    agent_info: Dict[str, str] = {}
    market_insights: Optional[Dict] = None
    voice_metrics: Optional[Dict] = None
    conversation_dynamics: Optional[Dict] = None

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
    async def transcribe_audio(self, request: TranscriptionRequest) -> Dict:
        """
        Transcribe audio using OpenAI's Whisper model with enhanced error handling and retry logic.
        """
        try:
            # Save audio bytes to temporary file
            temp_file = f"/tmp/audio_chunk_{datetime.now().timestamp()}.wav"
            try:
                with open(temp_file, "wb") as f:
                    f.write(request.audio_data)

                # Use OpenAI's Whisper model with the new client
                with open(temp_file, "rb") as audio_file:
                    transcription = await client.audio.transcriptions.create(
                        file=audio_file,
                        model="whisper-1",
                        language=request.language,
                        response_format="verbose_json"
                    )

                return {
                    "text": transcription.text,
                    "status": "success",
                    "timestamp": request.timestamp.isoformat(),
                    "confidence": getattr(transcription, "confidence", 1.0),
                    "language": getattr(transcription, "language", request.language)
                }

            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.remove(temp_file)

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def generate_suggestions(self, request: SuggestionRequest) -> List[Dict[str, str]]:
        """
        Generate context-aware suggestions using GPT-4 with enhanced error handling and retry logic.
        """
        try:
            # Format conversation history with more context
            conversation_context = "\n".join([
                f"{msg['speaker']}: {msg['text']}"
                for msg in request.conversation_history[-10:]  # Last 10 messages
            ])

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
                emotional_context = f"""
Client Voice Analysis:
- Confidence Level: {request.voice_metrics.get('emotion_scores', {}).get('confident', 0):.2f}
- Interest Level: {request.voice_metrics.get('emotion_scores', {}).get('interested', 0):.2f}
- Hesitation Level: {request.voice_metrics.get('emotion_scores', {}).get('hesitant', 0):.2f}
- Speaking Rate: {request.voice_metrics.get('speaking_rate', 0):.1f} words/min
- Overall Sentiment: {'Positive' if request.voice_metrics.get('emotion_scores', {}).get('positive', 0) > 0.5 else 'Negative'}"""

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

            # Enhanced prompt with all context
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

            # Get suggestions from GPT-4 with the new client
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

            # Process and format suggestions
            suggestions = []
            for choice in response.choices:
                suggestions.append({
                    "text": choice.message.content.strip(),
                    "confidence": float(choice.message.content_filter_results.get("confidence", 1.0)),
                    "type": "dynamic",
                    "context": {
                        "stage": request.current_stage,
                        "interest_level": request.interest_level,
                        "addressed_objections": [obj for obj in request.identified_objections if obj.lower() in choice.message.content.lower()]
                    }
                })

            return suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            # Provide more context-aware fallback suggestions
            fallback_suggestions = self._get_fallback_suggestions(request)
            return fallback_suggestions

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

            # Parse the JSON response
            analysis = json.loads(response.choices[0].message.content)
            return {
                "status": "success",
                **analysis,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error analyzing conversation: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "stage": "unknown",
                "objections": [],
                "interest_level": "unknown",
                "needs": [],
                "topics": [],
                "next_actions": ["Retry analysis"],
                "timestamp": datetime.now().isoformat()
            }

ai_service = AIService()
"""
Real-time suggestion generator using the conversation analyzer.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional
import logging
from ..core.conversation_analyzer import ConversationAnalyzer
from ..core.conversation_templates import (
    OPENING_SCRIPTS,
    OBJECTION_HANDLERS,
    ALM_QUESTIONS,
    CLOSING_TEMPLATES,
    AVOID_PHRASES,
    POSITIVE_PHRASES
)

logger = logging.getLogger(__name__)

class ConversationContext(BaseModel):
    """Model representing the current conversation context."""
    transcript: str
    last_segment: str
    current_stage: Optional[str] = None
    appointment_set: bool = False
    location_discussed: bool = False
    motivation_uncovered: bool = False

class SuggestionGenerator:
    def __init__(self):
        self.analyzer = ConversationAnalyzer()
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        
    async def generate_suggestions(self, context: ConversationContext) -> Dict:
        """
        Generate context-aware suggestions based on conversation analysis.
        
        Args:
            context: ConversationContext object containing conversation state
            
        Returns:
            Dict containing suggestions and analysis
        """
        try:
            # Analyze the last segment
            analysis = self.analyzer.analyze_speech(context.last_segment, self._detect_speaker(context.last_segment))
            
            # Update conversation stage
            context.current_stage = analysis['stage']
            
            # Generate primary suggestion
            primary_suggestion = self._get_primary_suggestion(analysis, context)
            
            # Generate alternative suggestions
            alternatives = self._get_alternative_suggestions(analysis, context)
            
            # Check for warnings
            warnings = analysis.get('warnings', [])
            
            # Get progress through ALM framework
            progress = self.analyzer.get_alm_progress()
            
            return {
                "status": "success",
                "primary_suggestion": primary_suggestion,
                "alternative_suggestions": alternatives,
                "warnings": warnings,
                "stage": context.current_stage,
                "progress": progress,
                "positive_phrases": self._get_relevant_positive_phrases(context.current_stage)
            }
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_primary_suggestion(self, analysis: Dict, context: ConversationContext) -> str:
        """Get the primary suggestion based on analysis."""
        if analysis.get('suggestion_type') == 'objection_handler':
            return analysis['suggestion']
        
        if not context.appointment_set:
            return ALM_QUESTIONS['appointment'][0]
        elif not context.location_discussed:
            return ALM_QUESTIONS['location'][0]
        elif not context.motivation_uncovered:
            return ALM_QUESTIONS['motivation'][0]
        else:
            return CLOSING_TEMPLATES['appointment_set']['template']
    
    def _get_alternative_suggestions(self, analysis: Dict, context: ConversationContext) -> List[str]:
        """Generate alternative suggestions based on context."""
        stage = context.current_stage
        alternatives = []
        
        if stage == 'appointment':
            alternatives.extend(ALM_QUESTIONS['appointment'][1:3])
        elif stage == 'location':
            alternatives.extend(ALM_QUESTIONS['location'][1:3])
        elif stage == 'motivation':
            alternatives.extend(ALM_QUESTIONS['motivation'][1:3])
        
        return alternatives
    
    def _get_relevant_positive_phrases(self, stage: str) -> List[str]:
        """Get positive phrases relevant to the current stage."""
        # Start with universal positive phrases
        phrases = ["I understand", "That's great", "Perfect"]
        
        # Add stage-specific phrases
        if stage == 'appointment':
            phrases.extend([
                "I'd be happy to show you the property",
                "That works perfectly",
                "I'm looking forward to meeting you"
            ])
        elif stage == 'location':
            phrases.extend([
                "That's a wonderful area",
                "I know that neighborhood well",
                "There are some great opportunities there"
            ])
        elif stage == 'motivation':
            phrases.extend([
                "I can definitely help you with that",
                "That makes perfect sense",
                "I appreciate you sharing that"
            ])
        elif stage == 'closing':
            phrases.extend([
                "I'm excited to work with you",
                "You've made a great decision",
                "I'll take care of everything"
            ])
            
        return phrases
    
    def _detect_speaker(self, text: str) -> str:
        """Detect whether the speaker is likely the agent or client."""
        text = text.lower()
        
        # Common agent phrases
        agent_indicators = [
            "this is",
            "with realty",
            "would you like to see",
            "i can show you",
            "are you available",
            "excited to work with you",
            "i understand",
            "let me",
            "i would be happy to"
        ]
        
        return "agent" if any(phrase in text for phrase in agent_indicators) else "client"

# Create singleton instance
suggestion_generator = SuggestionGenerator()
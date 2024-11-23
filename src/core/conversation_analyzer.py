"""
Real-time conversation analyzer for the Real Estate Call Assistant.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from .conversation_templates import (
    OPENING_SCRIPTS, 
    OBJECTION_HANDLERS, 
    ALM_QUESTIONS, 
    CLOSING_TEMPLATES,
    AVOID_PHRASES,
    POSITIVE_PHRASES
)

class ConversationStage(Enum):
    OPENING = "opening"
    APPOINTMENT = "appointment"
    LOCATION = "location"
    MOTIVATION = "motivation"
    OBJECTION_HANDLING = "objection_handling"
    CLOSING = "closing"

class ObjectionType(Enum):
    LISTING_AGENT = "listing_agent"
    WORKING_WITH_AGENT = "working_with_agent"
    QUICK_QUESTION = "quick_question"
    PENDING_PROPERTY = "pending_property"
    OUT_OF_TOWN = "out_of_town"
    NOT_READY = "not_ready"

@dataclass
class ConversationState:
    stage: ConversationStage
    appointment_set: bool = False
    location_discussed: bool = False
    motivation_uncovered: bool = False
    objections_handled: List[ObjectionType] = None
    last_speaker: str = None  # 'agent' or 'client'
    appointment_time: Optional[str] = None
    preferred_locations: List[str] = None
    motivation_factors: List[str] = None
    
    def __post_init__(self):
        self.objections_handled = self.objections_handled or []
        self.preferred_locations = self.preferred_locations or []
        self.motivation_factors = self.motivation_factors or []

class ConversationAnalyzer:
    def __init__(self):
        self.state = ConversationState(stage=ConversationStage.OPENING)
        self.call_duration = 0
        self.detected_objections = set()
        
    def analyze_speech(self, text: str, speaker: str) -> Dict:
        """
        Analyzes speech input and returns appropriate suggestions.
        
        Args:
            text: The transcribed speech text
            speaker: Either 'agent' or 'client'
            
        Returns:
            Dict containing suggestions and warnings
        """
        self.state.last_speaker = speaker
        text = text.lower()
        
        # Check for phrases to avoid
        warnings = self._check_avoid_phrases(text)
        
        # Detect objections
        objection = self._detect_objection(text)
        if objection:
            self.detected_objections.add(objection)
            return {
                'suggestion_type': 'objection_handler',
                'suggestion': OBJECTION_HANDLERS[objection.value],
                'warnings': warnings
            }
            
        # Process based on conversation stage
        if self.state.stage == ConversationStage.OPENING:
            return self._handle_opening_stage(text, speaker)
        elif self.state.stage == ConversationStage.APPOINTMENT:
            return self._handle_appointment_stage(text, speaker)
        elif self.state.stage == ConversationStage.LOCATION:
            return self._handle_location_stage(text, speaker)
        elif self.state.stage == ConversationStage.MOTIVATION:
            return self._handle_motivation_stage(text, speaker)
        elif self.state.stage == ConversationStage.CLOSING:
            return self._handle_closing_stage(text, speaker)
            
        return {'suggestion_type': 'general', 'warnings': warnings}

    def _check_avoid_phrases(self, text: str) -> List[str]:
        """Checks for phrases that should be avoided during the call."""
        warnings = []
        for phrase in AVOID_PHRASES:
            if phrase in text.lower():
                warnings.append(f"Avoid mentioning '{phrase}' during the first call")
        return warnings
        
    def _detect_objection(self, text: str) -> Optional[ObjectionType]:
        """Detects if the client has raised an objection."""
        text = text.lower()
        if "listing agent" in text or "seller's agent" in text:
            return ObjectionType.LISTING_AGENT
        elif "working with" in text and "agent" in text:
            return ObjectionType.WORKING_WITH_AGENT
        elif "quick question" in text or "just wondering" in text:
            return ObjectionType.QUICK_QUESTION
        elif "pending" in text or "under contract" in text:
            return ObjectionType.PENDING_PROPERTY
        elif "out of town" in text or "not in town" in text:
            return ObjectionType.OUT_OF_TOWN
        elif "not ready" in text or "too soon" in text:
            return ObjectionType.NOT_READY
        return None

    def _handle_opening_stage(self, text: str, speaker: str) -> Dict:
        """Handles the opening stage of the conversation."""
        if speaker == 'agent':
            # Check if the agent has properly introduced themselves
            if "this is" in text and ("realty" in text or "real estate" in text):
                self.state.stage = ConversationStage.APPOINTMENT
                return {
                    'suggestion_type': 'alm_question',
                    'suggestion': ALM_QUESTIONS['appointment'][0],
                    'next_stage': 'appointment'
                }
        return {
            'suggestion_type': 'opening',
            'suggestion': "Remember to introduce yourself and your brokerage"
        }

    def _handle_appointment_stage(self, text: str, speaker: str) -> Dict:
        """Handles the appointment stage of the conversation."""
        if speaker == 'client':
            # Look for positive appointment indicators
            if any(phrase in text.lower() for phrase in ["yes", "sure", "okay", "tomorrow", "available"]):
                self.state.appointment_set = True
                self.state.stage = ConversationStage.LOCATION
                return {
                    'suggestion_type': 'alm_question',
                    'suggestion': ALM_QUESTIONS['location'][0],
                    'next_stage': 'location'
                }
        return {
            'suggestion_type': 'appointment',
            'suggestion': "Focus on securing the appointment. Try: " + ALM_QUESTIONS['appointment'][0]
        }

    def _handle_location_stage(self, text: str, speaker: str) -> Dict:
        """Handles the location stage of the conversation."""
        if speaker == 'client':
            # Look for location preferences
            self.state.location_discussed = True
            self.state.stage = ConversationStage.MOTIVATION
            return {
                'suggestion_type': 'alm_question',
                'suggestion': ALM_QUESTIONS['motivation'][0],
                'next_stage': 'motivation'
            }
        return {
            'suggestion_type': 'location',
            'suggestion': "Ask about other areas they're interested in: " + ALM_QUESTIONS['location'][1]
        }

    def _handle_motivation_stage(self, text: str, speaker: str) -> Dict:
        """Handles the motivation stage of the conversation."""
        if speaker == 'client':
            # Look for motivation indicators
            self.state.motivation_uncovered = True
            self.state.stage = ConversationStage.CLOSING
            return {
                'suggestion_type': 'closing',
                'suggestion': CLOSING_TEMPLATES['appointment_set' if self.state.appointment_set else 'nurture_lead']['template'],
                'next_stage': 'closing'
            }
        return {
            'suggestion_type': 'motivation',
            'suggestion': "Uncover their motivation: " + ALM_QUESTIONS['motivation'][0]
        }

    def _handle_closing_stage(self, text: str, speaker: str) -> Dict:
        """Handles the closing stage of the conversation."""
        if speaker == 'agent':
            if "excited to work with you" in text.lower():
                return {
                    'suggestion_type': 'end_call',
                    'suggestion': "Great job! You've completed the ALM framework and ended positively."
                }
        return {
            'suggestion_type': 'closing',
            'suggestion': "Remember to end with 'I'm excited to work with you!'"
        }

    def get_alm_progress(self) -> Dict:
        """Returns the progress through the ALM framework."""
        return {
            'appointment': self.state.appointment_set,
            'location': self.state.location_discussed,
            'motivation': self.state.motivation_uncovered,
            'objections_handled': [obj.value for obj in self.state.objections_handled]
        }

    def get_next_question(self) -> str:
        """Returns the next appropriate question based on the current stage."""
        if not self.state.appointment_set:
            return ALM_QUESTIONS['appointment'][0]
        elif not self.state.location_discussed:
            return ALM_QUESTIONS['location'][0]
        elif not self.state.motivation_uncovered:
            return ALM_QUESTIONS['motivation'][0]
        return CLOSING_TEMPLATES['appointment_set']['template']
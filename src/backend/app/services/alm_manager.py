from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ALMStage(BaseModel):
    appointment: Dict[str, any] = {
        "secured": False,
        "date_time": None,
        "type": None,  # "in_person" or "video"
        "multiple_properties": False
    }
    location: Dict[str, any] = {
        "discussed": False,
        "preferences": [],
        "other_properties": False
    }
    motivation: Dict[str, any] = {
        "discussed": False,
        "interests": [],
        "search_duration": None
    }
    current_priority: str = "appointment"  # Tracks current focus: "appointment", "location", or "motivation"

class ALMManager:
    def __init__(self):
        self.appointment_questions = {
            "in_person": [
                "Great, when would you like to go see the property?",
                "Would tomorrow or the next day work better for viewing?",
                "Are mornings or afternoons better for you?"
            ],
            "video": [
                "Great, I'd be happy to get you a recorded video tour for that property or do a live video tour with you from the property so you can ask questions in real-time. What works best for you?"
            ],
            "alternative": [
                "When would you like to see other similar homes in the area?"
            ]
        }
        
        self.location_questions = [
            "Are there any other properties you've been looking at? I'd be happy to arrange tours for those as well.",
            "Are you only interested in this area, or are you open to seeing alternative locations and neighborhoods?"
        ]
        
        self.motivation_questions = [
            "What interests you about this property?",
            "How long have you been looking?",
            "Have you seen any other properties?"
        ]

    def get_next_question(self, alm_stage: ALMStage, property_available: bool = True) -> str:
        """Get the next appropriate question based on ALM stage and property availability."""
        
        # APPOINTMENT FIRST - Always try to secure the appointment first
        if not alm_stage.appointment["secured"]:
            if property_available:
                return self.appointment_questions["in_person"][0]
            else:
                return self.appointment_questions["alternative"][0]
                
        # LOCATION SECOND - Only after appointment is secured
        if not alm_stage.location["discussed"]:
            return self.location_questions[0]
            
        # MOTIVATION THIRD - Only after location is discussed
        if not alm_stage.motivation["discussed"]:
            return self.motivation_questions[0]
            
        # If everything is completed, focus on confirming appointment details
        return self._get_appointment_confirmation(alm_stage)

    def get_response_suggestions(self, 
                               alm_stage: ALMStage,
                               context: Dict[str, any]) -> List[str]:
        """Generate appropriate responses based on ALM stage and context."""
        suggestions = []
        
        # APPOINTMENT PHASE
        if not alm_stage.appointment["secured"]:
            suggestions.extend(self._get_appointment_suggestions(context))
            return suggestions  # Return immediately - focus on appointment
            
        # LOCATION PHASE
        if not alm_stage.location["discussed"]:
            suggestions.extend(self._get_location_suggestions(context))
            return suggestions  # Return immediately - focus on location
            
        # MOTIVATION PHASE
        if not alm_stage.motivation["discussed"]:
            suggestions.extend(self._get_motivation_suggestions(context))
            return suggestions

        # If all phases complete, focus on next steps
        suggestions.extend(self._get_next_steps_suggestions(alm_stage))
        return suggestions

    def _get_appointment_suggestions(self, context: Dict[str, any]) -> List[str]:
        """Generate appointment-focused suggestions with enthusiasm and positivity."""
        suggestions = []
        property_available = context.get("property_available", True)
        
        # Always focus on securing appointment first, regardless of property availability
        suggestions.extend([
            "I'm excited to help you find your perfect home! When would you like to go see this property?",
            "I'd love to show you this home! Are you available today or tomorrow? I'm happy to work around your schedule!",
            "This is such a great property - I can't wait to show it to you! Would morning or afternoon work better for your schedule?"
        ])
        
        # If property isn't available, we still maintain positivity and focus on alternatives
        if not property_available:
            suggestions.extend([
                "I'm really excited to show you some amazing properties in this area! When would be the best time for you?",
                "I have several fantastic homes that I think you'll love even more! Would tomorrow or the next day work better?",
                "Let me show you some incredible properties that just came on the market! What time works best for you?"
            ])
            
        # Add suggestions for multiple property viewings
        suggestions.extend([
            "While we're out, I'd love to show you a couple other amazing properties in the area! Would that interest you?",
            "I know of several other fantastic homes nearby - would you like to see those during the same visit?",
            "To make the most of your time, I'd be happy to show you multiple properties! Would that be helpful?"
        ])
            
        return suggestions

    def _get_location_suggestions(self, context: Dict[str, any]) -> List[str]:
        """Generate enthusiastic location-focused suggestions."""
        return [
            "I'd love to know about any other properties that have caught your eye! I can definitely arrange tours for those as well!",
            "This is a fantastic area! Are you specifically interested in this neighborhood, or would you like to explore some other amazing locations nearby?",
            "I know this market really well - would you like me to show you some other incredible properties in this area during our tour?",
            "While we're viewing this home, I'd be happy to show you some other fantastic properties nearby! Would that be helpful?",
            "I'm really excited to show you some other great options in this area! Would you like me to put together a tour of similar homes?"
        ]

    def _get_motivation_suggestions(self, context: Dict[str, any]) -> List[str]:
        """Generate rapport-building motivation questions."""
        return [
            "I'd love to hear what caught your attention about this property! What features really stood out to you?",
            "It's great that you're exploring homes in this area! How long have you been looking for your perfect home?",
            "I'm curious what inspired your home search! What made you start looking in this area?",
            "Every home search is unique - I'd love to hear what's most important to you in your next home!",
            "Your feedback really helps me find the perfect home for you! What features are you most excited about?"
        ]

    def _get_next_steps_suggestions(self, alm_stage: ALMStage) -> List[str]:
        """Generate enthusiastic next steps and closing suggestions."""
        suggestions = [
            self._get_appointment_confirmation(alm_stage),
            "I'm really excited to help you find your perfect home! I'll send you all the details of our appointment and the properties we'll be viewing right away!",
            "Thank you for taking the time to discuss your home search needs! I'll reach out to the sellers and prepare everything for our tours!",
            f"The phone number I have for you is {alm_stage.appointment.get('phone', '[phone]')} - is that correct? And what's your preferred method of communication?",
            "I'm very excited to work with you and help you find the perfect home! I'll get back to you shortly with all the appointment confirmations!"
        ]
        
        # If this might be a longer-term nurture lead
        if not alm_stage.appointment.get("secured"):
            suggestions.extend([
                "I'm happy to set you up on a search for properties that match exactly what we discussed! That way we can keep an eye on the market together!",
                "I'm excited to be your go-to agent! Please don't hesitate to reach out if you see any properties you'd like to discuss or if you have any questions!",
                "Thank you for sharing your home search plans with me! I'll keep an eye out for properties that match your criteria and reach out when I find something perfect!"
            ])
            
        return suggestions

    def _get_appointment_confirmation(self, alm_stage: ALMStage) -> str:
        """Generate enthusiastic appointment confirmation message."""
        if not alm_stage.appointment.get("date_time"):
            return "I'm excited to show you these properties! What time works best for your schedule?"
            
        viewing_type = "see" if alm_stage.appointment.get("type") == "in_person" else "do the video tour of"
        properties = "properties" if alm_stage.appointment.get("multiple_properties") else "property"
        
        return (
            f"Perfect! I'm really looking forward to our appointment! Just to confirm, we'll {viewing_type} the "
            f"{properties} at {alm_stage.appointment['date_time']}. I'm excited to help you explore these homes! "
            "I'll send you all the details right away!"
        )

    def analyze_response(self, 
                        response: str,
                        alm_stage: ALMStage) -> Tuple[ALMStage, List[str]]:
        """Analyze customer response and update ALM stage accordingly."""
        updated_stage = alm_stage.copy()
        next_steps = []
        
        # Check for appointment commitment
        if not updated_stage.appointment["secured"]:
            if self._check_appointment_commitment(response):
                updated_stage.appointment["secured"] = True
                updated_stage.current_priority = "location"
                next_steps.append("Secure appointment details")
                
        # Check for location discussion
        elif not updated_stage.location["discussed"]:
            if self._check_location_discussion(response):
                updated_stage.location["discussed"] = True
                updated_stage.current_priority = "motivation"
                next_steps.append("Note location preferences")
                
        # Check for motivation discussion
        elif not updated_stage.motivation["discussed"]:
            if self._check_motivation_discussion(response):
                updated_stage.motivation["discussed"] = True
                next_steps.append("Complete ALM process")
                
        return updated_stage, next_steps

    def _check_appointment_commitment(self, response: str) -> bool:
        """Check if response includes appointment commitment."""
        positive_indicators = ["yes", "sure", "okay", "tomorrow", "morning", "afternoon", "time"]
        return any(indicator in response.lower() for indicator in positive_indicators)

    def _check_location_discussion(self, response: str) -> bool:
        """Check if response includes location preferences."""
        location_indicators = ["area", "neighborhood", "location", "other properties", "looking"]
        return any(indicator in response.lower() for indicator in location_indicators)

    def _check_motivation_discussion(self, response: str) -> bool:
        """Check if response includes motivation information."""
        motivation_indicators = ["because", "interested", "looking for", "need", "want"]
        return any(indicator in response.lower() for indicator in motivation_indicators)

    def get_progress_report(self, alm_stage: ALMStage) -> Dict:
        """Generate a progress report for the ALM process."""
        return {
            "current_priority": alm_stage.current_priority,
            "appointment_secured": alm_stage.appointment["secured"],
            "location_discussed": alm_stage.location["discussed"],
            "motivation_discussed": alm_stage.motivation["discussed"],
            "next_step": self._get_next_step(alm_stage),
            "completion_status": self._get_completion_status(alm_stage)
        }

    def _get_next_step(self, alm_stage: ALMStage) -> str:
        """Determine the next step in the ALM process."""
        if not alm_stage.appointment["secured"]:
            return "Secure appointment"
        if not alm_stage.location["discussed"]:
            return "Discuss location preferences"
        if not alm_stage.motivation["discussed"]:
            return "Understand motivation"
        return "Complete - confirm appointment details"

    def _get_completion_status(self, alm_stage: ALMStage) -> str:
        """Calculate completion status of ALM process."""
        steps_completed = sum([
            alm_stage.appointment["secured"],
            alm_stage.location["discussed"],
            alm_stage.motivation["discussed"]
        ])
        percentage = (steps_completed / 3) * 100
        return f"{percentage:.0f}% complete"

alm_manager = ALMManager()
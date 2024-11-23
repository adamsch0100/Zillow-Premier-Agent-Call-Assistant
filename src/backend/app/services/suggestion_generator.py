from typing import List, Dict
import json
from pydantic import BaseModel
import re

class ConversationContext(BaseModel):
    transcript: str
    last_segment: str
    conversation_stage: str = "initial"
    identified_objections: List[str] = []
    conversation_history: List[Dict[str, str]] = []
    client_needs: List[str] = []
    interest_level: str = "unknown"
    property_details: Dict[str, str] = {}
    agent_info: Dict[str, str] = {}

class SuggestionGenerator:
    def __init__(self, db_session=None):
        from .script_manager import script_manager
        from .metrics_tracker import MetricsTracker
        self.script_manager = script_manager
        self.metrics_tracker = MetricsTracker(db_session) if db_session else None
        self.conversation_stages = [
            "initial",            # Initial greeting
            "alm_area",          # Getting area preferences
            "alm_location",      # Understanding location needs
            "alm_money",         # Qualifying budget/financing
            "objection_handling", # Handle any objections
            "appointment_setting" # Set the appointment
        ]
        self.stage_confidence_weights = {
            "initial": 1.0,
            "rapport_building": 0.9,
            "needs_analysis": 0.85,
            "qualification": 0.8,
            "objection_handling": 0.95,
            "closing": 0.75
        }
        
    def _determine_current_stage(self, context: ConversationContext) -> str:
        """Determine the current conversation stage based on context and history."""
        if not context.conversation_history:
            return "initial"
        
        exchange_count = len(context.conversation_history)
        last_customer_msg = next(
            (msg for msg in reversed(context.conversation_history) 
             if msg.get("speaker") == "customer"),
            None
        )

        # Check for objections in the last customer message
        if last_customer_msg:
            objections = self.script_manager.identify_objections(last_customer_msg["text"])
            if objections:
                return "objection_handling"

        # Determine stage based on conversation progression
        if exchange_count <= 2:
            return "initial"
        elif exchange_count <= 4:
            return "rapport_building"
        elif exchange_count <= 6:
            return "needs_analysis"
        elif exchange_count <= 8:
            return "qualification"
        else:
            recent_responses = [
                msg["text"].lower() 
                for msg in context.conversation_history[-3:]
                if msg.get("speaker") == "customer"
            ]
            
            positive_signals = sum(
                1 for text in recent_responses
                if any(word in text for word in 
                      ["yes", "okay", "sure", "interested", "when", "schedule", "see"])
            )
            
            return "closing" if positive_signals >= 2 else "qualification"
            
    def _load_objection_patterns(self) -> Dict[str, List[str]]:
        # Now we use the script manager's patterns instead
        if hasattr(self.script_manager, 'scripts') and 'objection_handlers' in self.script_manager.scripts:
            patterns = {}
            for objection_type, handler in self.script_manager.scripts['objection_handlers'].items():
                patterns[objection_type] = handler.get('patterns', [])

    async def analyze_conversation(self, context: ConversationContext) -> Dict:
        """Analyze conversation using AI to detect stage/objections."""
        try:
            from .openai_service import ai_service
            
            # First use regex patterns for quick detection
            objections = []
            for obj_type, patterns in self.objection_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, context.last_segment.lower()):
                        objections.append(obj_type)
                        break
            
            # Then use AI for deeper analysis
            analysis = await ai_service.analyze_conversation(context.transcript)
            
            if analysis["status"] == "success":
                return analysis
            else:
                # Fallback to basic analysis if AI fails
                stage = "initial"
                if objections:
                    stage = f"objection_{objections[0]}"
                return {
                    "stage": stage,
                    "objections": objections,
                    "interest_level": "unknown",
                    "needs": []
                }
                
        except Exception as e:
            print(f"Error in conversation analysis: {e}")
            return {
                "stage": "initial",
                "objections": [],
                "interest_level": "unknown",
                "needs": []
            }

    async def generate_suggestions(self, context: ConversationContext, conversation_id: str = None) -> List[Dict[str, str]]:
        """Generate context-aware suggestions using a combination of AI and templates."""
        try:
            from .openai_service import ai_service, SuggestionRequest
            import logging
            logger = logging.getLogger(__name__)
            import os
            
            # Update conversation stage
            current_stage = self._determine_current_stage(context)
            context.conversation_stage = current_stage
            
            # Get AI analysis for deeper understanding
            analysis = await self.analyze_conversation(context)
            
            # Update context with analysis results
            context.identified_objections.extend(analysis.get("objections", []))
            context.interest_level = analysis.get("interest_level", context.interest_level)
            if "needs" in analysis:
                context.client_needs.extend(analysis["needs"])
            
            # Initialize suggestion collectors
            ai_suggestions = []
            template_suggestions = []
            qualifying_questions = []
            
            # Get AI-generated suggestions
            try:
                request = SuggestionRequest(
                    transcript=context.transcript,
                    conversation_history=context.conversation_history[-10:],
                    current_stage=current_stage,
                    identified_objections=list(set(context.identified_objections)),
                    client_needs=context.client_needs,
                    interest_level=context.interest_level,
                    property_details=context.property_details,
                    agent_info=context.agent_info
                )
                ai_suggestions = await ai_service.generate_suggestions(request)
            except Exception as e:
                logger.error(f"Error getting AI suggestions: {e}")
                
            # Get template suggestions based on stage
            try:
                if current_stage == "initial":
                    template_suggestions.extend([
                        {
                            "text": self.script_manager._fill_template(greeting, context.agent_info, context.property_details),
                            "confidence": 0.9,
                            "type": "initial_greeting"
                        }
                        for greeting in self.script_manager.scripts.get("initial_contact", {}).get("regular", [])[:2]
                    ])
                    
                elif current_stage == "objection_handling":
                    # Get objection-specific responses
                    for objection in context.identified_objections:
                        responses = self.script_manager.get_objection_response(objection, {
                            "agent_info": context.agent_info,
                            "property_info": context.property_details
                        })
                        template_suggestions.extend([
                            {
                                "text": response,
                                "confidence": 0.85,
                                "type": f"objection_{objection}"
                            }
                            for response in responses[:2]
                        ])
                        
                elif current_stage == "closing":
                    # Add closing statements
                    template_suggestions.extend([
                        {
                            "text": stmt,
                            "confidence": 0.8,
                            "type": "closing"
                        }
                        for stmt in self.script_manager.get_closing_statements(
                            {"agent_info": context.agent_info, "property_info": context.property_details},
                            "schedule_viewing"
                        )[:2]
                    ])
                
                # Add qualifying questions based on stage
                if current_stage in ["rapport_building", "needs_analysis", "qualification"]:
                    questions = []
                    if "timeline" not in [need.lower() for need in context.client_needs]:
                        questions.extend(self.script_manager.get_qualifying_questions("timeline")[:1])
                    if "preferences" not in [need.lower() for need in context.client_needs]:
                        questions.extend(self.script_manager.get_qualifying_questions("preferences")[:1])
                    if "budget" not in [need.lower() for need in context.client_needs]:
                        questions.extend(self.script_manager.get_qualifying_questions("budget")[:1])
                        
                    qualifying_questions = [
                        {
                            "text": question,
                            "confidence": 0.75,
                            "type": "qualifying_question"
                        }
                        for question in questions
                    ]
                    
            except Exception as e:
                logger.error(f"Error getting template suggestions: {e}")
            
            # Combine all suggestions
            all_suggestions = ai_suggestions + template_suggestions + qualifying_questions
            
            # Remove duplicates and similar suggestions
            unique_suggestions = self._remove_similar_suggestions(all_suggestions)
            
            # Sort by confidence and relevance
            sorted_suggestions = sorted(
                unique_suggestions,
                key=lambda x: (x["confidence"], -len(x["text"])),  # Higher confidence, shorter text
                reverse=True
            )
            
            # Track suggestions if metrics tracking is enabled
            if self.metrics_tracker and conversation_id:
                for suggestion in sorted_suggestions:
                    await self.metrics_tracker.track_suggestion(
                        conversation_id=conversation_id,
                        suggestion=suggestion,
                        was_used=False
                    )

            # Return top suggestions
            max_suggestions = int(os.getenv('MAX_SUGGESTIONS', '3'))
            top_suggestions = sorted_suggestions[:max_suggestions]

            # Add tracking IDs to suggestions if metrics enabled
            if self.metrics_tracker and conversation_id:
                for suggestion in top_suggestions:
                    suggestion["tracking_id"] = f"{conversation_id}_{datetime.utcnow().timestamp()}"

            return top_suggestions
            
        except Exception as e:
            logger.error(f"Error in generate_suggestions: {e}")
            # Fallback to basic greeting
            return [
                {
                    "text": "Hi, this is an agent. How can I help you today?",
                    "confidence": 0.5,
                    "type": "fallback"
                }
            ]
    
    def _fill_template(self, template: str, context: ConversationContext) -> str:
        """Fill template with context-specific information."""
        replacements = {
            "[agent name]": context.agent_info.get("name", ""),
            "[brokerage]": context.agent_info.get("brokerage", ""),
            "[property]": context.property_details.get("address", "the property"),
            "[price]": context.property_details.get("price", ""),
            "[bedrooms]": context.property_details.get("bedrooms", ""),
            "[bathrooms]": context.property_details.get("bathrooms", "")
        }
        
        result = template
        for key, value in replacements.items():
            result = result.replace(key, value if value else key)
        return result
    
    def _remove_similar_suggestions(self, suggestions: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove suggestions that are too similar to each other."""
        unique_suggestions = []
        for suggestion in suggestions:
            is_unique = True
            for unique_suggestion in unique_suggestions:
                if self._calculate_similarity(
                    suggestion["text"],
                    unique_suggestion["text"]
                ) > 0.8:  # Similarity threshold
                    is_unique = False
                    break
            if is_unique:
                unique_suggestions.append(suggestion)
        return unique_suggestions
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts using simple token overlap."""
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        return len(intersection) / len(union) if union else 0.0

suggestion_generator = SuggestionGenerator()
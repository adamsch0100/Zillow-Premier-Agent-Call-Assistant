import json
import re
from typing import List, Dict, Optional
from pathlib import Path
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class ScriptManager:
    def __init__(self):
        self.scripts = self._load_scripts()
        self._compile_patterns()

    def _load_scripts(self) -> Dict:
        """Load scripts from JSON file."""
        try:
            script_path = Path(__file__).parent.parent / "data" / "scripts" / "zillow_scripts.json"
            with open(script_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading scripts: {e}")
            return {}

    def _compile_patterns(self):
        """Compile regex patterns for objection handlers."""
        if 'objection_handlers' in self.scripts:
            for objection_type, handler in self.scripts['objection_handlers'].items():
                handler['compiled_patterns'] = [
                    re.compile(pattern, re.IGNORECASE)
                    for pattern in handler['patterns']
                ]

    def get_initial_greeting(self, agent_info: Dict[str, str], property_info: Dict[str, str], is_voicemail: bool = False) -> str:
        """Get appropriate initial greeting based on context."""
        greeting_type = "voicemail" if is_voicemail else "regular"
        greetings = self.scripts.get("initial_contact", {}).get(greeting_type, [])
        
        if not greetings:
            return None

        # Select greeting (could be enhanced with more sophisticated selection logic)
        greeting = greetings[0]
        
        # Fill in template variables
        return self._fill_template(greeting, agent_info, property_info)

    def identify_objections(self, text: str) -> List[Dict[str, any]]:
        """Identify objections in the given text."""
        objections = []
        
        if 'objection_handlers' not in self.scripts:
            return objections

        for objection_type, handler in self.scripts['objection_handlers'].items():
            for pattern in handler['compiled_patterns']:
                if pattern.search(text):
                    objections.append({
                        'type': objection_type,
                        'responses': handler['responses'],
                        'confidence': 0.9  # Could be adjusted based on pattern match quality
                    })
                    break  # Found match for this objection type

        return objections

    def get_qualifying_questions(self, category: Optional[str] = None) -> List[str]:
        """Get qualifying questions, optionally filtered by category."""
        if 'qualifying_questions' not in self.scripts:
            return []

        if category and category in self.scripts['qualifying_questions']:
            return self.scripts['qualifying_questions'][category]
        
        # If no category specified or invalid category, return all questions
        all_questions = []
        for category_questions in self.scripts['qualifying_questions'].values():
            all_questions.extend(category_questions)
        return all_questions

    def get_closing_statements(self, 
                             context: Dict[str, any],
                             category: Optional[str] = None) -> List[str]:
        """Get appropriate closing statements based on context and category."""
        if 'closing_statements' not in self.scripts:
            return []

        if category and category in self.scripts['closing_statements']:
            statements = self.scripts['closing_statements'][category]
        else:
            # Combine all closing statements
            statements = []
            for cat_statements in self.scripts['closing_statements'].values():
                statements.extend(cat_statements)

        # Fill in templates
        return [
            self._fill_template(
                statement,
                context.get('agent_info', {}),
                context.get('property_info', {})
            )
            for statement in statements
        ]

    def get_objection_response(self, 
                             objection_type: str,
                             context: Dict[str, any] = None) -> List[str]:
        """Get appropriate responses for a specific objection type."""
        if 'objection_handlers' not in self.scripts:
            return []

        handler = self.scripts['objection_handlers'].get(objection_type)
        if not handler:
            return []

        responses = handler.get('responses', [])
        if context:
            return [
                self._fill_template(
                    response,
                    context.get('agent_info', {}),
                    context.get('property_info', {})
                )
                for response in responses
            ]
        return responses

    def _fill_template(self, 
                      template: str,
                      agent_info: Dict[str, str],
                      property_info: Dict[str, str]) -> str:
        """Fill in template variables with actual values."""
        # Basic template variables
        replacements = {
            '[agent name]': agent_info.get('name', ''),
            '[brokerage]': agent_info.get('brokerage', ''),
            '[phone]': agent_info.get('phone', ''),
            '[property]': property_info.get('address', 'the property'),
            '[price]': property_info.get('price', ''),
            '[bedrooms]': property_info.get('bedrooms', ''),
            '[bathrooms]': property_info.get('bathrooms', ''),
            '[sqft]': property_info.get('sqft', ''),
            '[year built]': property_info.get('year_built', ''),
            '[day/time]': 'afternoon',  # Could be dynamic based on current time
            '[X]': '7'  # Could be dynamic based on market data
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, str(value) if value else key)
        return result

    def get_conversation_starters(self, context: Dict[str, any]) -> List[str]:
        """Get appropriate conversation starters based on context."""
        starters = []
        
        # Add property-specific questions
        if context.get('property_info'):
            starters.extend([
                f"What attracted you to this {context['property_info'].get('style', 'home')}?",
                f"Are you familiar with the {context['property_info'].get('neighborhood', 'area')}?",
                "What features are you looking for in your next home?"
            ])

        # Add timeline questions
        starters.extend(self.get_qualifying_questions('timeline'))

        return starters

    def get_next_best_questions(self, 
                              conversation_stage: str,
                              asked_questions: List[str] = None) -> List[str]:
        """Get the next best questions to ask based on conversation stage."""
        asked_questions = asked_questions or []
        
        if conversation_stage == "initial":
            questions = self.get_qualifying_questions('motivation')
        elif conversation_stage == "qualification":
            questions = self.get_qualifying_questions('preferences')
        elif conversation_stage == "needs_analysis":
            questions = self.get_qualifying_questions('timeline')
        elif conversation_stage == "closing":
            questions = self.scripts.get('closing_statements', {}).get('schedule_viewing', [])
        else:
            questions = self.get_qualifying_questions()

        # Filter out already asked questions
        return [q for q in questions if q not in asked_questions]

script_manager = ScriptManager()
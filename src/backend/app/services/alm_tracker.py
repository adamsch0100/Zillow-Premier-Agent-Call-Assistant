from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel
from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

class ALMStatus(BaseModel):
    area: Dict[str, Optional[str]] = {
        "value": None,
        "confidence": None,
        "timestamp": None
    }
    location_needs: Dict[str, Optional[str]] = {
        "value": None,
        "confidence": None,
        "timestamp": None
    }
    money: Dict[str, Optional[str]] = {
        "value": None,
        "confidence": None,
        "timestamp": None
    }
    completion_percentage: float = 0.0
    is_qualified: bool = False
    missing_elements: List[str] = []
    next_question: Optional[str] = None

class ALMTracker:
    def __init__(self):
        # Core ALM questions with variations
        self.alm_questions = {
            "area": [
                "What areas are you interested in?",
                "Which neighborhoods are you considering?",
                "What parts of [city] appeal to you most?",
                "Where are you looking to buy?"
            ],
            "location_needs": [
                "What's most important to you about the location?",
                "What do you need to be close to?",
                "Are there specific features you're looking for in the location?",
                "What's your ideal commute time?"
            ],
            "money": [
                "Have you spoken with a lender about your purchase price range?",
                "What price range are you comfortable with?",
                "Have you been pre-approved for a mortgage?",
                "What monthly payment works for your budget?"
            ]
        }

        # ALM completion indicators
        self.alm_indicators = {
            "area": [
                r'\b(?:looking|interested|want|prefer|like)\s+(?:in|around|near)\s+([A-Za-z\s]+(?:area|neighborhood|suburb|city|town|district))',
                r'\b(?:north|south|east|west|downtown)\s+[A-Za-z\s]+',
                r'\b[A-Za-z\s]+(?:area|neighborhood|suburb|city|town|district)\b'
            ],
            "location_needs": [
                r'\b(?:close|near|proximity)\s+to\s+([A-Za-z\s]+)',
                r'\b(?:school|work|shopping|transportation|highway|train|bus)\s+(?:district|access|nearby|area)',
                r'\b(?:commute|drive|travel)\s+time\b',
                r'\b(?:walkable|quiet|suburban|urban|rural)\b'
            ],
            "money": [
                r'\b(?:budget|afford|price|cost|payment)\s+(?:range|around|about|between)?\s+(?:\$?\d[\d,.]*K?|thousand|million)',
                r'\b(?:pre-?approved|approved|qualified)\b',
                r'\b(?:lender|mortgage|loan|financing)\b',
                r'\bdown\s+payment\b'
            ]
        }

    async def analyze_conversation(self, transcript: str) -> ALMStatus:
        """Analyze conversation for ALM completion."""
        status = ALMStatus()
        
        # Check each ALM component
        for component, patterns in self.alm_indicators.items():
            confidence = 0.0
            value = None
            
            for pattern in patterns:
                matches = re.finditer(pattern, transcript, re.IGNORECASE)
                for match in matches:
                    confidence = max(confidence, 0.8)  # Found direct mention
                    value = match.group(0)
                    
                    # Extract specific values if available
                    if component == "money" and re.search(r'\$?\d', value):
                        # Clean and standardize money values
                        value = self._standardize_money(value)
                        confidence = 0.9
                    
            if value:
                status_dict = {
                    "value": value,
                    "confidence": confidence,
                    "timestamp": datetime.now().isoformat()
                }
                setattr(status, component, status_dict)

        # Calculate completion and missing elements
        status.completion_percentage = self._calculate_completion(status)
        status.missing_elements = self._get_missing_elements(status)
        status.is_qualified = status.completion_percentage >= 0.8
        status.next_question = self._get_next_question(status)

        return status

    def _standardize_money(self, value: str) -> str:
        """Standardize money expressions to a consistent format."""
        # Remove non-numeric characters except K,M,k,m
        clean_value = re.sub(r'[^\d.,KkMm]', '', value)
        
        # Convert K/M notation to full numbers
        if re.search(r'[Kk]$', clean_value):
            clean_value = str(int(float(clean_value.rstrip('Kk')) * 1000))
        elif re.search(r'[Mm]$', clean_value):
            clean_value = str(int(float(clean_value.rstrip('Mm')) * 1000000))
            
        return f"${clean_value:,}"

    def _calculate_completion(self, status: ALMStatus) -> float:
        """Calculate ALM completion percentage."""
        completed = 0
        total_components = 3
        
        if status.area["value"]:
            completed += 1
        if status.location_needs["value"]:
            completed += 1
        if status.money["value"]:
            completed += 1
            
        return completed / total_components

    def _get_missing_elements(self, status: ALMStatus) -> List[str]:
        """Identify missing ALM elements."""
        missing = []
        
        if not status.area["value"]:
            missing.append("area")
        if not status.location_needs["value"]:
            missing.append("location_needs")
        if not status.money["value"]:
            missing.append("money")
            
        return missing

    def _get_next_question(self, status: ALMStatus) -> Optional[str]:
        """Get the next most appropriate ALM question."""
        if not status.money["value"]:
            return self.alm_questions["money"][0]
        elif not status.area["value"]:
            return self.alm_questions["area"][0]
        elif not status.location_needs["value"]:
            return self.alm_questions["location_needs"][0]
        return None

    def get_alm_suggestion(self, status: ALMStatus) -> str:
        """Get appropriate suggestion based on ALM status."""
        if status.is_qualified:
            return ("Great! I have a clear picture of what you're looking for. "
                   "Would you like to schedule a time to view some properties that match your criteria?")
        
        if status.next_question:
            return status.next_question
            
        missing = status.missing_elements[0] if status.missing_elements else None
        if missing:
            return self.alm_questions[missing][0]
            
        return "Let's schedule a time to look at some properties that match your criteria."

    def generate_alm_based_suggestions(self, status: ALMStatus) -> List[str]:
        """Generate suggestions focused on completing ALM and setting appointment."""
        suggestions = []
        
        # If fully qualified, focus on appointment setting
        if status.is_qualified:
            suggestions.extend([
                "I have several properties that match your criteria. Would tomorrow or the next day work better for viewing?",
                "Based on what you've shared, I can show you some great options. Are mornings or afternoons better for you?",
                "I've got some properties that fit your needs perfectly. When would you like to take a look?"
            ])
            return suggestions

        # If not qualified, focus on gathering missing ALM information
        missing = status.missing_elements
        if missing:
            for element in missing:
                suggestions.append(self.alm_questions[element][0])
                
        # Add transitional suggestion if we're close to complete
        if status.completion_percentage >= 0.66:
            suggestions.append(
                "Just one more quick question before I show you some great properties that match what you're looking for..."
            )
            
        return suggestions

    def get_alm_progress_report(self, status: ALMStatus) -> Dict:
        """Generate a progress report for ALM qualification."""
        return {
            "completion_percentage": status.completion_percentage,
            "is_qualified": status.is_qualified,
            "collected_info": {
                "area": status.area["value"],
                "location_needs": status.location_needs["value"],
                "money": status.money["value"]
            },
            "missing_elements": status.missing_elements,
            "next_steps": "Set appointment" if status.is_qualified else f"Collect {', '.join(status.missing_elements)}"
        }

alm_tracker = ALMTracker()
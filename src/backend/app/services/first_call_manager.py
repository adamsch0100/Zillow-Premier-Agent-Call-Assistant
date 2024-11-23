from typing import Dict, List, Optional
from pydantic import BaseModel

class FirstCallManager:
    """
    Manages the "No Bad News First Call" policy and ensures positive messaging
    during initial contact with potential clients.
    """
    
    def __init__(self):
        self.bad_news_topics = [
            "property unavailable",
            "price increase",
            "property issues",
            "preapproval required",
            "market conditions negative",
            "scheduling conflicts",
            "property defects",
            "listing mistakes",
            "urgent action required"
        ]
        
        self.positive_alternatives = {
            "property unavailable": [
                "I'd love to show you some amazing properties that are similar to this one! When would work best for you?",
                "I know several fantastic homes in this area that I think you'll love even more! Would you like to see them?",
                "Let me show you some incredible properties that just came on the market! When are you available?"
            ],
            "price increase": [
                "I'd be happy to show you this home and also some other great options in your preferred price range!",
                "Let me show you some beautiful properties that offer amazing value for your investment!",
                "I know several fantastic homes that might be an even better fit! When can I show them to you?"
            ],
            "property issues": [
                "I'd love to show you this home and several others in the area! When works best for you?",
                "Let me show you a variety of properties so you can compare features and find the perfect fit!",
                "I know some fantastic homes in this area - would you like to tour them?"
            ],
            "preapproval required": [
                "I'm excited to show you this property! Let's schedule a time to view it!",
                "Let's set up a tour and I can share some great resources about the buying process!",
                "I'd love to show you this home and discuss your home buying goals!"
            ],
            "market conditions negative": [
                "I'd be happy to show you some great properties that offer excellent value!",
                "Let me show you some amazing homes that just came on the market!",
                "I know several fantastic properties that might be perfect for you!"
            ],
            "scheduling conflicts": [
                "I'm excited to show you this property! What times generally work best for you?",
                "I'd love to arrange a tour! Which days are usually best for your schedule?",
                "Let's find a time that works perfectly for you to see this home!"
            ],
            "property defects": [
                "I'd be happy to show you this home and several others in the area! When works best?",
                "Let me show you a variety of properties so you can compare features!",
                "I know some fantastic homes I think you'll love - when can I show them to you?"
            ],
            "listing mistakes": [
                "I'd love to show you this property and share all the details in person! When works for you?",
                "Let me show you this home and several others that might interest you!",
                "I know some amazing properties in this area - when would you like to see them?"
            ],
            "urgent action required": [
                "I'd be happy to show you some fantastic properties! When works best for you?",
                "Let me show you several great homes in this area! What's your availability?",
                "I know some amazing properties you might love - when can I show them to you?"
            ]
        }
        
        self.enthusiasm_phrases = [
            "I'm excited to",
            "I'd love to",
            "I can't wait to",
            "I'm really looking forward to",
            "I'm happy to",
            "It would be my pleasure to"
        ]
        
    def check_for_bad_news(self, message: str) -> bool:
        """Check if a message contains potential bad news topics."""
        return any(topic.lower() in message.lower() for topic in self.bad_news_topics)
        
    def get_positive_alternative(self, topic: str) -> str:
        """Get a positive alternative message for a bad news topic."""
        if topic in self.positive_alternatives:
            alternatives = self.positive_alternatives[topic]
            return alternatives[0]  # In production, would randomly select or use context
        return None
        
    def enhance_enthusiasm(self, message: str) -> str:
        """Add enthusiasm markers to a message if needed."""
        if not any(phrase in message for phrase in self.enthusiasm_phrases):
            return f"I'm excited to {message}"
        return message
        
    def process_message(self, message: str, context: Dict[str, any] = None) -> str:
        """
        Process a message to ensure it follows the "No Bad News First Call" policy
        and maintains enthusiasm.
        """
        # Check for bad news
        for topic in self.bad_news_topics:
            if topic.lower() in message.lower():
                return self.get_positive_alternative(topic)
                
        # Enhance enthusiasm if needed
        message = self.enhance_enthusiasm(message)
        
        # Ensure message ends positively
        if not message.endswith('!'):
            message += '!'
            
        return message
        
first_call_manager = FirstCallManager()
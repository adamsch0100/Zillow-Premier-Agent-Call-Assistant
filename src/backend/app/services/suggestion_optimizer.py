from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OptimizationContext(BaseModel):
    voice_metrics: Optional[Dict[str, Any]]
    market_insights: Optional[Dict[str, Any]]
    conversation_dynamics: Optional[Dict[str, Any]]
    stage: str
    objections: List[str]
    needs: List[str]
    interest_level: str

class SuggestionOptimizer:
    def __init__(self):
        self.interest_threshold = 0.7
        self.hesitation_threshold = 0.6
        self.engagement_threshold = 0.5
        
        # Weights for different aspects of suggestion scoring
        self.weights = {
            "market_relevance": 0.25,
            "emotional_match": 0.25,
            "urgency": 0.2,
            "engagement": 0.15,
            "objection_handling": 0.15
        }

    def optimize_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> List[Dict[str, Any]]:
        """Optimize and rank suggestions based on all available signals."""
        try:
            # Score each suggestion
            scored_suggestions = []
            for suggestion in suggestions:
                scores = {
                    "market_relevance": self._score_market_relevance(suggestion, context),
                    "emotional_match": self._score_emotional_match(suggestion, context),
                    "urgency": self._score_urgency(suggestion, context),
                    "engagement": self._score_engagement(suggestion, context),
                    "objection_handling": self._score_objection_handling(suggestion, context)
                }
                
                # Calculate weighted score
                total_score = sum(
                    score * self.weights[aspect]
                    for aspect, score in scores.items()
                )
                
                scored_suggestions.append({
                    **suggestion,
                    "optimization_scores": scores,
                    "total_score": total_score
                })
            
            # Sort by total score
            scored_suggestions.sort(key=lambda x: x["total_score"], reverse=True)
            
            # Adjust suggestions based on conversation state
            final_suggestions = self._adjust_suggestions(scored_suggestions, context)
            
            return final_suggestions
            
        except Exception as e:
            logger.error(f"Error optimizing suggestions: {e}")
            return suggestions

    def _score_market_relevance(
        self,
        suggestion: Dict[str, Any],
        context: OptimizationContext
    ) -> float:
        """Score how well the suggestion uses market insights."""
        if not context.market_insights:
            return 0.5
            
        text = suggestion["text"].lower()
        market_terms = [
            "market", "price", "value", "trend", "similar",
            "median", "comparison", "inventory", "days on market"
        ]
        
        # Check for market term usage
        term_usage = sum(1 for term in market_terms if term in text)
        
        # Check for specific market data references
        has_price = "$" in text or "dollar" in text
        has_trends = "%" in text or "percent" in text
        has_timing = "days" in text or "quickly" in text
        
        score = (
            (term_usage / len(market_terms)) * 0.4 +
            (has_price * 0.2) +
            (has_trends * 0.2) +
            (has_timing * 0.2)
        )
        
        return min(1.0, score)

    def _score_emotional_match(
        self,
        suggestion: Dict[str, Any],
        context: OptimizationContext
    ) -> float:
        """Score how well the suggestion matches emotional state."""
        if not context.voice_metrics:
            return 0.5
            
        text = suggestion["text"].lower()
        metrics = context.voice_metrics
        
        # Get emotional signals
        confidence = metrics.get("emotion_scores", {}).get("confident", 0.5)
        hesitation = metrics.get("emotion_scores", {}).get("hesitant", 0.5)
        interest = metrics.get("emotion_scores", {}).get("interested", 0.5)
        
        # Define emotional language patterns
        reassuring_terms = ["understand", "appreciate", "help you", "let me", "share"]
        confidence_terms = ["definitely", "absolutely", "certainly", "great opportunity"]
        interest_building_terms = ["unique", "special", "perfect", "ideal", "exclusive"]
        
        # Score based on emotional needs
        if hesitation > self.hesitation_threshold:
            # Should use more reassuring language
            score = sum(1 for term in reassuring_terms if term in text) / len(reassuring_terms)
        elif confidence > 0.7:
            # Can use more direct language
            score = sum(1 for term in confidence_terms if term in text) / len(confidence_terms)
        else:
            # Focus on building interest
            score = sum(1 for term in interest_building_terms if term in text) / len(interest_building_terms)
            
        return min(1.0, score)

    def _score_urgency(
        self,
        suggestion: Dict[str, Any],
        context: OptimizationContext
    ) -> float:
        """Score how well the suggestion creates appropriate urgency."""
        if not context.market_insights:
            return 0.5
            
        text = suggestion["text"].lower()
        market_status = context.market_insights.get("market_status", "")
        days_on_market = context.market_insights.get("days_on_market", 30)
        
        urgency_terms = {
            "seller's market": [
                "quickly", "fast", "won't last", "competitive",
                "multiple", "soon", "today", "now"
            ],
            "buyer's market": [
                "opportunity", "advantage", "favorable",
                "potential", "negotiate", "value"
            ]
        }
        
        terms_to_check = urgency_terms.get(market_status, [])
        if terms_to_check:
            term_usage = sum(1 for term in terms_to_check if term in text)
            score = term_usage / len(terms_to_check)
        else:
            score = 0.5
            
        # Adjust based on days on market
        if days_on_market < 7:
            score *= 1.2  # Increase urgency for hot properties
            
        return min(1.0, score)

    def _score_engagement(
        self,
        suggestion: Dict[str, Any],
        context: OptimizationContext
    ) -> float:
        """Score how well the suggestion promotes engagement."""
        if not context.conversation_dynamics:
            return 0.5
            
        text = suggestion["text"].lower()
        
        # Check for engagement elements
        has_question = "?" in text
        has_invitation = any(term in text for term in [
            "would you", "could you", "what if", "how about",
            "tell me", "share with me"
        ])
        has_acknowledgment = any(term in text for term in [
            "understand", "hear", "appreciate", "interesting"
        ])
        
        # Calculate base score
        score = (
            (has_question * 0.4) +
            (has_invitation * 0.3) +
            (has_acknowledgment * 0.3)
        )
        
        # Adjust based on current engagement
        engagement_score = context.conversation_dynamics.get("engagement_score", 0.5)
        if engagement_score < self.engagement_threshold:
            # Increase weight of questions and invitations
            score *= 1.2
            
        return min(1.0, score)

    def _score_objection_handling(
        self,
        suggestion: Dict[str, Any],
        context: OptimizationContext
    ) -> float:
        """Score how well the suggestion handles relevant objections."""
        if not context.objections:
            return 0.5
            
        text = suggestion["text"].lower()
        
        # Keywords for effective objection handling
        objection_patterns = {
            "price_too_high": ["value", "worth", "investment", "comparable", "market"],
            "just_looking": ["help", "guide", "information", "explore", "options"],
            "need_time": ["understand", "process", "when", "timeline", "flexible"],
            "need_to_sell": ["assist", "coordinate", "strategy", "handle", "plan"],
            "location": ["area", "neighborhood", "community", "convenient", "located"]
        }
        
        scores = []
        for objection in context.objections:
            patterns = objection_patterns.get(objection, [])
            if patterns:
                matches = sum(1 for pattern in patterns if pattern in text)
                scores.append(matches / len(patterns))
                
        return max(scores) if scores else 0.5

    def _adjust_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        context: OptimizationContext
    ) -> List[Dict[str, Any]]:
        """Make final adjustments to suggestions based on context."""
        # Ensure variety in suggestion types
        final_suggestions = []
        added_types = set()
        
        for suggestion in suggestions:
            suggestion_type = self._categorize_suggestion(suggestion["text"])
            
            # Avoid too many similar suggestions
            if suggestion_type not in added_types or len(final_suggestions) < 2:
                added_types.add(suggestion_type)
                final_suggestions.append(suggestion)
                
            if len(final_suggestions) >= 3:
                break
                
        return final_suggestions

    def _categorize_suggestion(self, text: str) -> str:
        """Categorize suggestion type for variety checking."""
        if "?" in text:
            return "question"
        elif any(term in text.lower() for term in ["schedule", "tour", "visit", "show"]):
            return "appointment"
        elif any(term in text.lower() for term in ["market", "price", "value", "trend"]):
            return "market_info"
        elif any(term in text.lower() for term in ["understand", "hear", "appreciate"]):
            return "empathy"
        else:
            return "other"

suggestion_optimizer = SuggestionOptimizer()
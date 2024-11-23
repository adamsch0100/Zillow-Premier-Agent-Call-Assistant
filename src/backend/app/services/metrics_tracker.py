"""
Metrics tracking service for analyzing conversation effectiveness and suggestion performance.
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
from sqlalchemy.orm import Session
from ..models.metrics import ConversationMetrics, SuggestionMetrics
from ..models.conversation import Conversation
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class MetricsTracker:
    def __init__(self, db: Session):
        self.db = db
        self.current_metrics = {}
        
    async def start_conversation(self, conversation_id: str, agent_id: str) -> None:
        """Initialize metrics tracking for a new conversation."""
        try:
            metrics = ConversationMetrics(
                conversation_id=conversation_id,
                agent_id=agent_id,
                start_time=datetime.utcnow(),
                suggestion_count=0,
                suggestion_usage=0,
                objection_count=0,
                successful_objection_handles=0,
                qualifying_questions_asked=0,
                needs_identified=0,
                conversation_length=0
            )
            self.db.add(metrics)
            await self.db.commit()
            
            self.current_metrics[conversation_id] = {
                "suggestion_history": [],
                "objection_history": [],
                "needs_identified": set(),
                "questions_asked": set(),
                "start_time": datetime.utcnow(),
                "message_count": 0
            }
        except Exception as e:
            logger.error(f"Error starting metrics tracking: {e}")
            
    async def track_suggestion(self, 
                             conversation_id: str,
                             suggestion: Dict,
                             was_used: bool = False,
                             response_delay: Optional[float] = None) -> None:
        """Track a suggestion and its usage."""
        try:
            metrics = SuggestionMetrics(
                conversation_id=conversation_id,
                suggestion_text=suggestion["text"],
                suggestion_type=suggestion["type"],
                confidence_score=suggestion.get("confidence", 0.0),
                was_used=was_used,
                response_delay=response_delay,
                timestamp=datetime.utcnow()
            )
            self.db.add(metrics)
            await self.db.commit()
            
            if conversation_id in self.current_metrics:
                self.current_metrics[conversation_id]["suggestion_history"].append({
                    "text": suggestion["text"],
                    "type": suggestion["type"],
                    "was_used": was_used,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            logger.error(f"Error tracking suggestion: {e}")
            
    async def track_objection(self,
                            conversation_id: str,
                            objection_type: str,
                            was_handled: bool = False) -> None:
        """Track objection detection and handling success."""
        try:
            if conversation_id in self.current_metrics:
                self.current_metrics[conversation_id]["objection_history"].append({
                    "type": objection_type,
                    "was_handled": was_handled,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                # Update conversation metrics
                metrics = await self.db.query(ConversationMetrics).filter(
                    ConversationMetrics.conversation_id == conversation_id
                ).first()
                
                if metrics:
                    metrics.objection_count += 1
                    if was_handled:
                        metrics.successful_objection_handles += 1
                    await self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking objection: {e}")
            
    async def track_need_identified(self,
                                  conversation_id: str,
                                  need: str) -> None:
        """Track when a customer need is identified."""
        try:
            if conversation_id in self.current_metrics:
                self.current_metrics[conversation_id]["needs_identified"].add(need)
                
                # Update conversation metrics
                metrics = await self.db.query(ConversationMetrics).filter(
                    ConversationMetrics.conversation_id == conversation_id
                ).first()
                
                if metrics:
                    metrics.needs_identified = len(
                        self.current_metrics[conversation_id]["needs_identified"]
                    )
                    await self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking need: {e}")
            
    async def track_qualifying_question(self,
                                     conversation_id: str,
                                     question: str) -> None:
        """Track when a qualifying question is asked."""
        try:
            if conversation_id in self.current_metrics:
                self.current_metrics[conversation_id]["questions_asked"].add(question)
                
                # Update conversation metrics
                metrics = await self.db.query(ConversationMetrics).filter(
                    ConversationMetrics.conversation_id == conversation_id
                ).first()
                
                if metrics:
                    metrics.qualifying_questions_asked = len(
                        self.current_metrics[conversation_id]["questions_asked"]
                    )
                    await self.db.commit()
        except Exception as e:
            logger.error(f"Error tracking qualifying question: {e}")
            
    async def end_conversation(self,
                             conversation_id: str,
                             outcome: str = None) -> Dict:
        """End metrics tracking for a conversation and return summary."""
        try:
            if conversation_id not in self.current_metrics:
                return {}
                
            end_time = datetime.utcnow()
            duration = (end_time - self.current_metrics[conversation_id]["start_time"]).seconds
            
            # Update conversation metrics
            metrics = await self.db.query(ConversationMetrics).filter(
                ConversationMetrics.conversation_id == conversation_id
            ).first()
            
            if metrics:
                metrics.end_time = end_time
                metrics.duration = duration
                metrics.outcome = outcome
                await self.db.commit()
                
                # Generate summary
                summary = {
                    "duration": duration,
                    "message_count": self.current_metrics[conversation_id]["message_count"],
                    "objections_handled": len([
                        obj for obj in self.current_metrics[conversation_id]["objection_history"]
                        if obj["was_handled"]
                    ]),
                    "needs_identified": len(self.current_metrics[conversation_id]["needs_identified"]),
                    "questions_asked": len(self.current_metrics[conversation_id]["questions_asked"]),
                    "suggestions_used": len([
                        sug for sug in self.current_metrics[conversation_id]["suggestion_history"]
                        if sug["was_used"]
                    ]),
                    "outcome": outcome
                }
                
                # Calculate success metrics
                summary["objection_handle_rate"] = (
                    summary["objections_handled"] / len(self.current_metrics[conversation_id]["objection_history"])
                    if self.current_metrics[conversation_id]["objection_history"] else 0
                )
                
                summary["suggestion_usage_rate"] = (
                    summary["suggestions_used"] / len(self.current_metrics[conversation_id]["suggestion_history"])
                    if self.current_metrics[conversation_id]["suggestion_history"] else 0
                )
                
                # Clean up current metrics
                del self.current_metrics[conversation_id]
                
                return summary
        except Exception as e:
            logger.error(f"Error ending metrics tracking: {e}")
            return {}
            
    async def get_performance_metrics(self,
                                    agent_id: Optional[str] = None,
                                    start_date: Optional[datetime] = None,
                                    end_date: Optional[datetime] = None,
                                    include_trends: bool = False) -> Dict:
        """Get comprehensive performance metrics with optional trend analysis."""
        try:
            query = self.db.query(ConversationMetrics)
            
            if agent_id:
                query = query.filter(ConversationMetrics.agent_id == agent_id)
            if start_date:
                query = query.filter(ConversationMetrics.start_time >= start_date)
            if end_date:
                query = query.filter(ConversationMetrics.end_time <= end_date)
                
            metrics = await query.all()
            
            if not metrics:
                return {}
                
            # Calculate base metrics
            total_conversations = len(metrics)
            total_duration = sum(m.duration for m in metrics if m.duration)
            total_objections = sum(m.objection_count for m in metrics)
            total_handled = sum(m.successful_objection_handles for m in metrics)
            total_suggestions = sum(m.suggestion_count for m in metrics)
            total_used = sum(m.suggestion_usage for m in metrics)
            
            # Get top performing suggestions
            suggestion_query = self.db.query(SuggestionMetrics)\
                .filter(SuggestionMetrics.conversation_id.in_([m.conversation_id for m in metrics]))
            suggestion_metrics = await suggestion_query.all()
            
            suggestion_performance = {}
            for sm in suggestion_metrics:
                if sm.suggestion_text not in suggestion_performance:
                    suggestion_performance[sm.suggestion_text] = {
                        "uses": 0,
                        "successes": 0,
                        "type": sm.suggestion_type
                    }
                suggestion_performance[sm.suggestion_text]["uses"] += 1
                if sm.was_used:
                    suggestion_performance[sm.suggestion_text]["successes"] += 1
            
            top_suggestions = [
                {
                    "text": text,
                    "usage_count": data["uses"],
                    "success_rate": data["successes"] / data["uses"] if data["uses"] > 0 else 0,
                    "type": data["type"]
                }
                for text, data in suggestion_performance.items()
                if data["uses"] >= 5  # Minimum threshold for significance
            ]
            
            # Sort by success rate and usage count
            top_suggestions.sort(key=lambda x: (x["success_rate"], x["usage_count"]), reverse=True)
            
            # Calculate improvement areas
            improvement_areas = []
            if total_objections > 0 and total_handled / total_objections < 0.8:
                improvement_areas.append("objection_handling")
            if total_suggestions > 0 and total_used / total_suggestions < 0.6:
                improvement_areas.append("suggestion_relevance")
            avg_questions = sum(m.qualifying_questions_asked for m in metrics) / total_conversations
            if avg_questions < 3:
                improvement_areas.append("need_discovery")
            
            # Generate trend data if requested
            trend_data = {}
            if include_trends:
                # Group metrics by day
                daily_metrics = {}
                for metric in metrics:
                    day = metric.start_time.date()
                    if day not in daily_metrics:
                        daily_metrics[day] = {
                            "conversations": 0,
                            "duration": 0,
                            "objections_handled": 0,
                            "suggestions_used": 0
                        }
                    daily_metrics[day]["conversations"] += 1
                    daily_metrics[day]["duration"] += metric.duration or 0
                    daily_metrics[day]["objections_handled"] += metric.successful_objection_handles
                    daily_metrics[day]["suggestions_used"] += metric.suggestion_usage
                
                # Convert to lists for trending
                trend_data = {
                    "daily_conversations": [
                        daily_metrics[day]["conversations"]
                        for day in sorted(daily_metrics.keys())
                    ],
                    "avg_duration_trend": [
                        daily_metrics[day]["duration"] / daily_metrics[day]["conversations"]
                        for day in sorted(daily_metrics.keys())
                    ],
                    "success_rate_trend": [
                        (daily_metrics[day]["objections_handled"] + daily_metrics[day]["suggestions_used"]) /
                        (daily_metrics[day]["conversations"] * 2)  # Normalize to 0-1 range
                        for day in sorted(daily_metrics.keys())
                    ]
                }
            
            return {
                "total_conversations": total_conversations,
                "avg_duration": total_duration / total_conversations if total_conversations else 0,
                "objection_handle_rate": total_handled / total_objections if total_objections else 0,
                "suggestion_usage_rate": total_used / total_suggestions if total_suggestions else 0,
                "avg_needs_identified": sum(m.needs_identified for m in metrics) / total_conversations,
                "avg_qualifying_questions": avg_questions,
                "outcomes": {
                    outcome: len([m for m in metrics if m.outcome == outcome])
                    for outcome in set(m.outcome for m in metrics if m.outcome)
                },
                "top_performing_suggestions": top_suggestions[:10],  # Top 10 suggestions
                "improvement_areas": improvement_areas,
                "trend_analysis": trend_data if include_trends else None
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}

    async def get_objection_analysis(self,
                                   agent_id: Optional[str] = None,
                                   date_range: Optional[Dict] = None,
                                   min_occurrences: int = 5) -> List[Dict]:
        """Analyze objection patterns and handling effectiveness."""
        try:
            # Build base query for conversations
            conv_query = self.db.query(ConversationMetrics)
            if agent_id:
                conv_query = conv_query.filter(ConversationMetrics.agent_id == agent_id)
            if date_range:
                if date_range.start_date:
                    conv_query = conv_query.filter(ConversationMetrics.start_time >= date_range.start_date)
                if date_range.end_date:
                    conv_query = conv_query.filter(ConversationMetrics.end_time <= date_range.end_date)

            conversations = await conv_query.all()
            if not conversations:
                return []

            # Collect objection data from conversations
            objection_data = {}
            
            # Analyze objections from conversation history
            for conv in conversations:
                # Get associated suggestion metrics for objection responses
                suggestion_metrics = await self.db.query(SuggestionMetrics)\
                    .filter(SuggestionMetrics.conversation_id == conv.conversation_id)\
                    .filter(SuggestionMetrics.suggestion_type.like('objection_%'))\
                    .all()

                for sm in suggestion_metrics:
                    objection_type = sm.suggestion_type.replace('objection_', '')
                    
                    if objection_type not in objection_data:
                        objection_data[objection_type] = {
                            "count": 0,
                            "successful_handles": 0,
                            "total_resolution_time": 0,
                            "responses": {},
                            "contexts": set()
                        }
                    
                    objection_data[objection_type]["count"] += 1
                    if sm.was_used:
                        objection_data[objection_type]["successful_handles"] += 1
                        objection_data[objection_type]["responses"][sm.suggestion_text] = \
                            objection_data[objection_type]["responses"].get(sm.suggestion_text, 0) + 1
                    
                    if sm.response_delay:
                        objection_data[objection_type]["total_resolution_time"] += sm.response_delay
                    
                    if sm.context_data:
                        stage = sm.context_data.get("conversation_stage")
                        if stage:
                            objection_data[objection_type]["contexts"].add(stage)

            # Filter and format results
            analysis_results = []
            for objection_type, data in objection_data.items():
                if data["count"] >= min_occurrences:
                    # Sort responses by effectiveness
                    sorted_responses = sorted(
                        data["responses"].items(),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    analysis_results.append({
                        "objection_type": objection_type,
                        "occurrence_count": data["count"],
                        "success_rate": data["successful_handles"] / data["count"] if data["count"] > 0 else 0,
                        "avg_resolution_time": data["total_resolution_time"] / data["count"] if data["count"] > 0 else 0,
                        "most_effective_responses": [resp[0] for resp in sorted_responses[:3]],
                        "common_contexts": list(data["contexts"])
                    })

            # Sort by occurrence count
            analysis_results.sort(key=lambda x: x["occurrence_count"], reverse=True)
            return analysis_results

        except Exception as e:
            logger.error(f"Error analyzing objections: {e}")
            return []

    async def get_daily_metrics(self,
                              agent_id: Optional[str] = None,
                              start_date: datetime = None,
                              end_date: datetime = None) -> List[Dict]:
        """Get detailed daily metrics breakdown."""
        try:
            # Build base query
            query = self.db.query(ConversationMetrics)
            if agent_id:
                query = query.filter(ConversationMetrics.agent_id == agent_id)
            if start_date:
                query = query.filter(ConversationMetrics.start_time >= start_date)
            if end_date:
                query = query.filter(ConversationMetrics.end_time <= end_date)

            conversations = await query.all()
            
            # Group metrics by day
            daily_data = {}
            for conv in conversations:
                day = conv.start_time.date()
                if day not in daily_data:
                    daily_data[day] = {
                        "conversation_count": 0,
                        "total_duration": 0,
                        "objections_handled": 0,
                        "suggestions_used": 0,
                        "needs_identified": 0,
                        "qualifying_questions": 0,
                        "successful_outcomes": 0
                    }

                daily_data[day]["conversation_count"] += 1
                daily_data[day]["total_duration"] += conv.duration or 0
                daily_data[day]["objections_handled"] += conv.successful_objection_handles
                daily_data[day]["suggestions_used"] += conv.suggestion_usage
                daily_data[day]["needs_identified"] += conv.needs_identified
                daily_data[day]["qualifying_questions"] += conv.qualifying_questions_asked
                if conv.outcome in ["appointment_set", "tour_scheduled", "offer_made"]:
                    daily_data[day]["successful_outcomes"] += 1

            # Calculate daily metrics and format results
            daily_metrics = []
            for day, data in sorted(daily_data.items()):
                conv_count = data["conversation_count"]
                if conv_count > 0:
                    daily_metrics.append({
                        "date": day,
                        "conversation_count": conv_count,
                        "avg_duration": data["total_duration"] / conv_count,
                        "success_rate": data["successful_outcomes"] / conv_count,
                        "key_metrics": {
                            "objections_per_call": data["objections_handled"] / conv_count,
                            "suggestions_per_call": data["suggestions_used"] / conv_count,
                            "needs_per_call": data["needs_identified"] / conv_count,
                            "questions_per_call": data["qualifying_questions"] / conv_count
                        }
                    })

            return daily_metrics

        except Exception as e:
            logger.error(f"Error getting daily metrics: {e}")
            return []

    async def get_agent_performance(self,
                                  agent_id: str,
                                  date_range: Optional[Dict] = None) -> Dict:
        """Get comprehensive agent performance analysis."""
        try:
            # Get base metrics
            performance_metrics = await self.get_performance_metrics(
                agent_id=agent_id,
                start_date=date_range.start_date if date_range else None,
                end_date=date_range.end_date if date_range else None,
                include_trends=True
            )

            # Get objection analysis
            objection_analysis = await self.get_objection_analysis(
                agent_id=agent_id,
                date_range=date_range,
                min_occurrences=3  # Lower threshold for individual agent analysis
            )

            # Calculate strengths and areas for improvement
            strengths = []
            improvements = []

            # Analyze objection handling
            if performance_metrics.get("objection_handle_rate", 0) >= 0.8:
                strengths.append("Strong objection handling skills")
            elif performance_metrics.get("objection_handle_rate", 0) < 0.6:
                improvements.append("Work on objection handling techniques")

            # Analyze suggestion usage
            if performance_metrics.get("suggestion_usage_rate", 0) >= 0.7:
                strengths.append("Effective use of suggested responses")
            elif performance_metrics.get("suggestion_usage_rate", 0) < 0.5:
                improvements.append("Increase use of system suggestions")

            # Analyze qualifying questions
            avg_questions = performance_metrics.get("avg_qualifying_questions", 0)
            if avg_questions >= 4:
                strengths.append("Thorough needs assessment")
            elif avg_questions < 3:
                improvements.append("Ask more qualifying questions")

            # Analyze conversion rates
            outcomes = performance_metrics.get("outcomes", {})
            success_outcomes = sum(
                count for outcome, count in outcomes.items()
                if outcome in ["appointment_set", "tour_scheduled", "offer_made"]
            )
            total_outcomes = sum(outcomes.values())
            conversion_rate = success_outcomes / total_outcomes if total_outcomes > 0 else 0

            if conversion_rate >= 0.4:
                strengths.append("Strong conversion rate")
            elif conversion_rate < 0.2:
                improvements.append("Focus on closing techniques")

            # Analyze conversation duration
            avg_duration = performance_metrics.get("avg_duration", 0)
            if 300 <= avg_duration <= 900:  # 5-15 minutes
                strengths.append("Optimal conversation duration")
            elif avg_duration < 180:  # Less than 3 minutes
                improvements.append("Extend conversation engagement")
            elif avg_duration > 1200:  # More than 20 minutes
                improvements.append("Work on conversation efficiency")

            # Get trend data
            trend_data = performance_metrics.get("trend_analysis", {})

            return {
                "agent_id": agent_id,
                "total_conversations": performance_metrics.get("total_conversations", 0),
                "avg_duration": performance_metrics.get("avg_duration", 0),
                "success_rate": conversion_rate,
                "strengths": strengths,
                "areas_for_improvement": improvements,
                "trend_data": trend_data,
                "top_objections": [
                    {
                        "type": obj["objection_type"],
                        "success_rate": obj["success_rate"],
                        "best_response": obj["most_effective_responses"][0] if obj["most_effective_responses"] else None
                    }
                    for obj in objection_analysis[:3]  # Top 3 objections
                ] if objection_analysis else []
            }

        except Exception as e:
            logger.error(f"Error getting agent performance: {e}")
            return {}
"""
Pydantic models for metrics tracking and analysis.
"""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class DateRange(BaseModel):
    start_date: datetime
    end_date: datetime

class ConversationMetricsCreate(BaseModel):
    conversation_id: str
    agent_id: str

class SuggestionFeedback(BaseModel):
    conversation_id: str
    tracking_id: str
    suggestion_text: str
    suggestion_type: str
    was_used: bool
    response_delay: Optional[float] = None
    customer_response: Optional[str] = None
    effectiveness_rating: Optional[int] = Field(None, ge=1, le=5)

class ConversationMetricsResponse(BaseModel):
    duration: int  # seconds
    message_count: int
    objections_handled: int
    needs_identified: int
    questions_asked: int
    suggestions_used: int
    objection_handle_rate: float
    suggestion_usage_rate: float
    outcome: Optional[str] = None

class SuggestionMetricsDetail(BaseModel):
    suggestion_text: str
    suggestion_type: str
    usage_count: int
    success_rate: float
    avg_response_delay: Optional[float]
    effectiveness_score: float
    context_stages: List[str]

class PerformanceMetricsResponse(BaseModel):
    total_conversations: int
    avg_duration: float  # seconds
    objection_handle_rate: float
    suggestion_usage_rate: float
    avg_needs_identified: float
    avg_qualifying_questions: float
    outcomes: Dict[str, int]
    top_performing_suggestions: Optional[List[SuggestionMetricsDetail]]
    improvement_areas: Optional[List[str]]
    trend_analysis: Optional[Dict[str, List[float]]]

class ObjectionAnalysis(BaseModel):
    objection_type: str
    occurrence_count: int
    success_rate: float
    avg_resolution_time: float
    most_effective_responses: List[str]
    common_contexts: List[str]

class DailyMetrics(BaseModel):
    date: datetime
    conversation_count: int
    avg_duration: float
    success_rate: float
    key_metrics: Dict[str, float]

class AgentPerformance(BaseModel):
    agent_id: str
    total_conversations: int
    avg_duration: float
    success_rate: float
    strengths: List[str]
    areas_for_improvement: List[str]
    trend_data: Dict[str, List[float]]

class MetricsFilter(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    agent_id: Optional[str] = None
    conversation_type: Optional[str] = None
    outcome_type: Optional[str] = None
    min_duration: Optional[int] = None
    max_duration: Optional[int] = None
    
class ConversationStageMetrics(BaseModel):
    stage: str
    avg_duration: float
    success_rate: float
    common_objections: List[str]
    effective_questions: List[str]
    next_stage_conversion_rate: float

class LearningMetrics(BaseModel):
    suggestion_improvements: List[Dict[str, any]]
    objection_pattern_updates: List[Dict[str, any]]
    new_effective_phrases: List[str]
    context_pattern_discoveries: List[Dict[str, any]]

class MetricsInsights(BaseModel):
    key_findings: List[str]
    improvement_recommendations: List[str]
    success_patterns: List[Dict[str, any]]
    risk_patterns: List[Dict[str, any]]
    opportunity_areas: List[str]

class MetricsExport(BaseModel):
    time_period: str
    data_points: List[Dict[str, any]]
    summary_statistics: Dict[str, float]
    agent_comparisons: Optional[List[Dict[str, any]]]
    conversion_funnels: Optional[List[Dict[str, any]]]
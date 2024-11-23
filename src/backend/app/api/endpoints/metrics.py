"""
API endpoints for metrics tracking and analysis.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ...core.database import get_db
from ...services.metrics_tracker import MetricsTracker
from ...schemas.metrics import (
    ConversationMetricsCreate,
    ConversationMetricsResponse,
    SuggestionFeedback,
    PerformanceMetricsResponse,
    DateRange,
    ObjectionAnalysis,
    DailyMetrics,
    AgentPerformance,
    MetricsFilter,
    ConversationStageMetrics,
    LearningMetrics,
    MetricsInsights,
    MetricsExport
)

router = APIRouter()

@router.post("/conversation/start", response_model=Dict[str, str])
async def start_conversation_tracking(
    data: ConversationMetricsCreate,
    db: Session = Depends(get_db)
):
    """Start tracking metrics for a new conversation."""
    metrics_tracker = MetricsTracker(db)
    await metrics_tracker.start_conversation(
        conversation_id=data.conversation_id,
        agent_id=data.agent_id
    )
    return {"status": "success", "conversation_id": data.conversation_id}

@router.post("/suggestion/feedback")
async def track_suggestion_feedback(
    feedback: SuggestionFeedback,
    db: Session = Depends(get_db)
):
    """Track whether a suggestion was used and its effectiveness."""
    metrics_tracker = MetricsTracker(db)
    await metrics_tracker.track_suggestion(
        conversation_id=feedback.conversation_id,
        suggestion={
            "text": feedback.suggestion_text,
            "type": feedback.suggestion_type,
            "tracking_id": feedback.tracking_id
        },
        was_used=feedback.was_used,
        response_delay=feedback.response_delay,
        effectiveness_rating=feedback.effectiveness_rating,
        customer_response=feedback.customer_response
    )
    return {"status": "success"}

@router.post("/conversation/objection")
async def track_objection(
    conversation_id: str,
    objection_type: str,
    was_handled: bool,
    resolution_time: Optional[float] = None,
    response_used: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Track objection detection and handling."""
    metrics_tracker = MetricsTracker(db)
    await metrics_tracker.track_objection(
        conversation_id=conversation_id,
        objection_type=objection_type,
        was_handled=was_handled,
        resolution_time=resolution_time,
        response_used=response_used
    )
    return {"status": "success"}

@router.post("/conversation/need")
async def track_need_identified(
    conversation_id: str,
    need: str,
    confidence: Optional[float] = None,
    context: Optional[Dict] = None,
    db: Session = Depends(get_db)
):
    """Track identified customer needs."""
    metrics_tracker = MetricsTracker(db)
    await metrics_tracker.track_need_identified(
        conversation_id=conversation_id,
        need=need,
        confidence=confidence,
        context=context
    )
    return {"status": "success"}

@router.post("/conversation/end", response_model=ConversationMetricsResponse)
async def end_conversation_tracking(
    conversation_id: str,
    outcome: Optional[str] = None,
    final_notes: Optional[Dict] = None,
    db: Session = Depends(get_db)
):
    """End conversation tracking and get summary metrics."""
    metrics_tracker = MetricsTracker(db)
    summary = await metrics_tracker.end_conversation(
        conversation_id=conversation_id,
        outcome=outcome,
        final_notes=final_notes
    )
    return summary

@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(
    agent_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    include_trends: bool = False,
    db: Session = Depends(get_db)
):
    """Get aggregated performance metrics."""
    metrics_tracker = MetricsTracker(db)
    
    # Set default date range to last 30 days if not specified
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)
    
    metrics = await metrics_tracker.get_performance_metrics(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date,
        include_trends=include_trends
    )
    return metrics

@router.get("/objections/analysis", response_model=List[ObjectionAnalysis])
async def get_objection_analysis(
    agent_id: Optional[str] = Query(None),
    date_range: Optional[DateRange] = None,
    min_occurrences: int = 5,
    db: Session = Depends(get_db)
):
    """Get detailed analysis of objection handling patterns."""
    metrics_tracker = MetricsTracker(db)
    analysis = await metrics_tracker.get_objection_analysis(
        agent_id=agent_id,
        date_range=date_range,
        min_occurrences=min_occurrences
    )
    return analysis

@router.get("/daily", response_model=List[DailyMetrics])
async def get_daily_metrics(
    agent_id: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """Get daily metrics breakdown."""
    metrics_tracker = MetricsTracker(db)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    daily_metrics = await metrics_tracker.get_daily_metrics(
        agent_id=agent_id,
        start_date=start_date,
        end_date=end_date
    )
    return daily_metrics

@router.get("/agent/{agent_id}/performance", response_model=AgentPerformance)
async def get_agent_performance(
    agent_id: str,
    date_range: Optional[DateRange] = None,
    db: Session = Depends(get_db)
):
    """Get detailed performance metrics for a specific agent."""
    metrics_tracker = MetricsTracker(db)
    performance = await metrics_tracker.get_agent_performance(
        agent_id=agent_id,
        date_range=date_range
    )
    return performance

@router.get("/conversation/stages", response_model=List[ConversationStageMetrics])
async def get_stage_metrics(
    agent_id: Optional[str] = Query(None),
    date_range: Optional[DateRange] = None,
    db: Session = Depends(get_db)
):
    """Get metrics broken down by conversation stages."""
    metrics_tracker = MetricsTracker(db)
    stage_metrics = await metrics_tracker.get_stage_metrics(
        agent_id=agent_id,
        date_range=date_range
    )
    return stage_metrics

@router.get("/learning", response_model=LearningMetrics)
async def get_learning_metrics(
    lookback_days: int = Query(30, ge=1, le=365),
    min_confidence: float = Query(0.8, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """Get metrics about system learning and improvements."""
    metrics_tracker = MetricsTracker(db)
    learning_metrics = await metrics_tracker.get_learning_metrics(
        lookback_days=lookback_days,
        min_confidence=min_confidence
    )
    return learning_metrics

@router.get("/insights", response_model=MetricsInsights)
async def get_metrics_insights(
    agent_id: Optional[str] = Query(None),
    date_range: Optional[DateRange] = None,
    db: Session = Depends(get_db)
):
    """Get AI-generated insights from metrics data."""
    metrics_tracker = MetricsTracker(db)
    insights = await metrics_tracker.get_insights(
        agent_id=agent_id,
        date_range=date_range
    )
    return insights

@router.post("/export", response_model=MetricsExport)
async def export_metrics(
    filters: MetricsFilter,
    include_agent_comparison: bool = False,
    include_funnels: bool = False,
    db: Session = Depends(get_db)
):
    """Export filtered metrics data."""
    metrics_tracker = MetricsTracker(db)
    export_data = await metrics_tracker.export_metrics(
        filters=filters,
        include_agent_comparison=include_agent_comparison,
        include_funnels=include_funnels
    )
    return export_data
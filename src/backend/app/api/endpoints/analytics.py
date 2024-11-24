from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Optional
from datetime import datetime, timedelta
from ...services.call_analytics import call_analytics

router = APIRouter()

@router.get("/metrics")
async def get_metrics(
    time_range: str = Query(
        "week",
        description="Time range for metrics: 'day', 'week', or 'month'"
    )
) -> Dict:
    """Get call analytics metrics for the specified time range."""
    try:
        end_date = datetime.now()
        
        if time_range == "day":
            start_date = end_date - timedelta(days=1)
        elif time_range == "week":
            start_date = end_date - timedelta(weeks=1)
        elif time_range == "month":
            start_date = end_date - timedelta(days=30)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid time range. Must be 'day', 'week', or 'month'"
            )

        metrics = call_analytics.get_aggregate_metrics(start_date, end_date)
        
        if metrics is None:
            raise HTTPException(
                status_code=500,
                detail="Failed to calculate metrics"
            )
            
        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching metrics: {str(e)}"
        )

@router.get("/metrics/{call_id}")
async def get_call_metrics(call_id: str) -> Dict:
    """Get detailed metrics for a specific call."""
    try:
        metrics = call_analytics.get_call_metrics(call_id)
        
        if metrics is None:
            raise HTTPException(
                status_code=404,
                detail=f"No metrics found for call {call_id}"
            )
            
        return metrics

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching call metrics: {str(e)}"
        )

@router.post("/metrics/{call_id}/objection")
async def track_objection_handling(
    call_id: str,
    objection_type: str = Query(..., description="Type of objection handled"),
    success: bool = Query(..., description="Whether the objection was handled successfully")
) -> Dict:
    """Track the success of objection handling during a call."""
    try:
        call_analytics.track_objection_handling(call_id, objection_type, success)
        return {"status": "success", "message": "Objection handling tracked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error tracking objection handling: {str(e)}"
        )

@router.post("/metrics/{call_id}/key-point")
async def record_key_point(
    call_id: str,
    point: str = Query(..., description="Key discussion point covered")
) -> Dict:
    """Record when a key discussion point is covered during a call."""
    try:
        call_analytics.record_key_point(call_id, point)
        return {"status": "success", "message": "Key point recorded successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error recording key point: {str(e)}"
        )
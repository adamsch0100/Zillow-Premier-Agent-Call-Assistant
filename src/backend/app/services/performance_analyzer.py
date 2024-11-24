from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict
import json
from pathlib import Path
import logging
from .call_analytics import CallAnalytics, call_analytics

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    def __init__(self):
        self.conversion_rate = 0.0
        self.avg_call_duration = 0.0
        self.objection_success_rate = 0.0
        self.key_points_coverage = 0.0
        self.client_engagement = 0.0
        self.alm_effectiveness = 0.0
        self.follow_up_rate = 0.0

class AgentPerformance:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.total_calls = 0
        self.successful_calls = 0
        self.total_duration = 0
        self.appointments_set = 0
        self.follow_ups_scheduled = 0
        self.objections_handled = 0
        self.successful_objections = 0
        self.alm_scores = []
        self.engagement_scores = []
        self.call_durations = []
        self.strengths = set()
        self.improvement_areas = set()

class PerformanceAnalyzer:
    def __init__(self):
        self.base_path = Path("/home/computeruse/real-estate-assistant/data/analytics/performance")
        self.ensure_directories()
        self.call_analytics = call_analytics
        self.agent_performances: Dict[str, AgentPerformance] = {}

    def ensure_directories(self):
        """Ensure required directories exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        (self.base_path / "agent_metrics").mkdir(exist_ok=True)
        (self.base_path / "trends").mkdir(exist_ok=True)

    def analyze_agent_performance(self, agent_id: str, start_date: datetime, end_date: datetime) -> Dict:
        """Analyze performance metrics for a specific agent."""
        performance = AgentPerformance(agent_id)
        
        # Get all call metrics for the agent
        calls = self._get_agent_calls(agent_id, start_date, end_date)
        
        for call in calls:
            performance.total_calls += 1
            performance.total_duration += call["duration"]
            performance.call_durations.append(call["duration"])
            
            # Track outcomes
            if call["outcomes"]["appointment_set"]:
                performance.appointments_set += 1
                performance.successful_calls += 1
            if call["outcomes"]["follow_up_scheduled"]:
                performance.follow_ups_scheduled += 1
            
            # Track ALM scores
            alm_score = sum(call["alm_completion"].values()) / 3
            performance.alm_scores.append(alm_score)
            
            # Track engagement
            performance.engagement_scores.append(call["engagement"]["score"])
        
        # Calculate derived metrics
        metrics = self._calculate_performance_metrics(performance)
        
        # Identify strengths and improvement areas
        self._analyze_performance_patterns(performance, metrics)
        
        return self._format_performance_report(performance, metrics)

    def _get_agent_calls(self, agent_id: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Retrieve all call metrics for an agent within the date range."""
        calls = []
        metrics_files = list((self.call_analytics.metrics_path).glob("*.json"))
        
        for file_path in metrics_files:
            try:
                with open(file_path, 'r') as f:
                    metrics = json.load(f)
                
                call_date = datetime.fromisoformat(metrics["start_time"])
                if (start_date <= call_date <= end_date and 
                    metrics.get("agent_id") == agent_id):
                    calls.append(metrics)
            except Exception as e:
                logger.error(f"Error reading metrics file {file_path}: {e}")
                
        return calls

    def _calculate_performance_metrics(self, performance: AgentPerformance) -> PerformanceMetrics:
        """Calculate performance metrics from raw data."""
        metrics = PerformanceMetrics()
        
        if performance.total_calls > 0:
            metrics.conversion_rate = performance.successful_calls / performance.total_calls
            metrics.avg_call_duration = np.mean(performance.call_durations)
            metrics.follow_up_rate = performance.follow_ups_scheduled / performance.total_calls
            
            if performance.objections_handled > 0:
                metrics.objection_success_rate = (
                    performance.successful_objections / performance.objections_handled
                )
            
            if performance.alm_scores:
                metrics.alm_effectiveness = np.mean(performance.alm_scores)
            
            if performance.engagement_scores:
                metrics.client_engagement = np.mean(performance.engagement_scores)
        
        return metrics

    def _analyze_performance_patterns(self, performance: AgentPerformance, metrics: PerformanceMetrics):
        """Identify strengths and areas for improvement."""
        # Clear previous analysis
        performance.strengths.clear()
        performance.improvement_areas.clear()
        
        # Threshold values for metrics
        thresholds = {
            "high_conversion": 0.3,
            "good_engagement": 0.7,
            "effective_alm": 0.8,
            "quick_calls": 600,  # 10 minutes
            "high_follow_up": 0.4
        }
        
        # Analyze conversion rate
        if metrics.conversion_rate >= thresholds["high_conversion"]:
            performance.strengths.add("High appointment conversion rate")
        elif metrics.conversion_rate < thresholds["high_conversion"] * 0.5:
            performance.improvement_areas.add("Appointment setting effectiveness")
        
        # Analyze engagement
        if metrics.client_engagement >= thresholds["good_engagement"]:
            performance.strengths.add("Strong client engagement")
        elif metrics.client_engagement < thresholds["good_engagement"] * 0.7:
            performance.improvement_areas.add("Client engagement and rapport building")
        
        # Analyze ALM framework usage
        if metrics.alm_effectiveness >= thresholds["effective_alm"]:
            performance.strengths.add("Effective ALM framework implementation")
        elif metrics.alm_effectiveness < thresholds["effective_alm"] * 0.6:
            performance.improvement_areas.add("ALM framework adherence")
        
        # Analyze call duration
        avg_duration = metrics.avg_call_duration
        if avg_duration <= thresholds["quick_calls"]:
            if metrics.conversion_rate >= thresholds["high_conversion"]:
                performance.strengths.add("Efficient call handling")
            else:
                performance.improvement_areas.add("Call duration optimization")
        
        # Analyze follow-up rate
        if metrics.follow_up_rate >= thresholds["high_follow_up"]:
            performance.strengths.add("Strong follow-up scheduling")
        elif metrics.follow_up_rate < thresholds["high_follow_up"] * 0.5:
            performance.improvement_areas.add("Follow-up scheduling rate")

    def _format_performance_report(self, performance: AgentPerformance, metrics: PerformanceMetrics) -> Dict:
        """Format the performance analysis into a detailed report."""
        return {
            "agent_id": performance.agent_id,
            "summary": {
                "total_calls": performance.total_calls,
                "successful_calls": performance.successful_calls,
                "total_duration": performance.total_duration,
                "appointments_set": performance.appointments_set,
                "follow_ups_scheduled": performance.follow_ups_scheduled
            },
            "metrics": {
                "conversion_rate": metrics.conversion_rate,
                "avg_call_duration": metrics.avg_call_duration,
                "objection_success_rate": metrics.objection_success_rate,
                "alm_effectiveness": metrics.alm_effectiveness,
                "client_engagement": metrics.client_engagement,
                "follow_up_rate": metrics.follow_up_rate
            },
            "trends": {
                "call_durations": self._calculate_trend(performance.call_durations),
                "alm_scores": self._calculate_trend(performance.alm_scores),
                "engagement_scores": self._calculate_trend(performance.engagement_scores)
            },
            "analysis": {
                "strengths": list(performance.strengths),
                "improvement_areas": list(performance.improvement_areas)
            }
        }

    def _calculate_trend(self, values: List[float]) -> Dict:
        """Calculate trend information for a series of values."""
        if not values:
            return {"trend": "neutral", "change": 0}
        
        # Calculate moving average
        window = min(5, len(values))
        if len(values) >= window:
            recent_avg = np.mean(values[-window:])
            earlier_avg = np.mean(values[:-window])
            change = (recent_avg - earlier_avg) / earlier_avg if earlier_avg != 0 else 0
            
            if change > 0.05:
                trend = "improving"
            elif change < -0.05:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
            change = 0
        
        return {
            "trend": trend,
            "change": change
        }

    def get_team_performance(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get aggregate performance metrics for the entire team."""
        team_metrics = {
            "total_calls": 0,
            "total_appointments": 0,
            "total_follow_ups": 0,
            "avg_conversion_rate": 0,
            "avg_engagement": 0,
            "avg_alm_effectiveness": 0,
            "top_performers": [],
            "improvement_needed": []
        }
        
        agent_metrics = {}
        metrics_files = list((self.call_analytics.metrics_path).glob("*.json"))
        
        for file_path in metrics_files:
            try:
                with open(file_path, 'r') as f:
                    metrics = json.load(f)
                
                call_date = datetime.fromisoformat(metrics["start_time"])
                if start_date <= call_date <= end_date:
                    agent_id = metrics.get("agent_id")
                    if agent_id not in agent_metrics:
                        agent_metrics[agent_id] = self.analyze_agent_performance(
                            agent_id, start_date, end_date
                        )
            except Exception as e:
                logger.error(f"Error processing metrics file {file_path}: {e}")
        
        # Calculate team averages
        if agent_metrics:
            for metrics in agent_metrics.values():
                team_metrics["total_calls"] += metrics["summary"]["total_calls"]
                team_metrics["total_appointments"] += metrics["summary"]["appointments_set"]
                team_metrics["total_follow_ups"] += metrics["summary"]["follow_ups_scheduled"]
            
            team_metrics["avg_conversion_rate"] = (
                team_metrics["total_appointments"] / team_metrics["total_calls"]
                if team_metrics["total_calls"] > 0 else 0
            )
            
            # Identify top performers and those needing improvement
            sorted_agents = sorted(
                agent_metrics.items(),
                key=lambda x: x[1]["metrics"]["conversion_rate"],
                reverse=True
            )
            
            team_metrics["top_performers"] = [
                {
                    "agent_id": agent_id,
                    "metrics": metrics["metrics"],
                    "strengths": metrics["analysis"]["strengths"]
                }
                for agent_id, metrics in sorted_agents[:3]
            ]
            
            team_metrics["improvement_needed"] = [
                {
                    "agent_id": agent_id,
                    "metrics": metrics["metrics"],
                    "improvement_areas": metrics["analysis"]["improvement_areas"]
                }
                for agent_id, metrics in sorted_agents[-3:]
            ]
        
        return team_metrics

performance_analyzer = PerformanceAnalyzer()
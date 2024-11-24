from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
import numpy as np
from collections import defaultdict
import logging
from .audio_processor import AudioSegment
from .alm_tracker import AlmStage

logger = logging.getLogger(__name__)

class CallMetrics:
    def __init__(self, call_id: str):
        self.call_id = call_id
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration = 0
        self.speech_ratio = 0.0
        self.agent_talk_ratio = 0.0
        self.client_talk_ratio = 0.0
        self.interruption_count = 0
        self.silence_ratio = 0.0
        self.alm_completion = {
            "appointment": 0.0,
            "location": 0.0,
            "motivation": 0.0
        }
        self.objection_handling_success = 0.0
        self.appointment_set = False
        self.follow_up_scheduled = False
        self.key_points_covered = set()
        self.sentiment_scores = []
        self.engagement_score = 0.0

class CallAnalytics:
    def __init__(self):
        self.base_path = Path("/home/computeruse/real-estate-assistant/data/analytics")
        self.metrics_path = self.base_path / "call_metrics"
        self.ensure_directories()
        self.current_metrics: Dict[str, CallMetrics] = {}
        self.sentiment_analyzer = None  # Will be initialized when needed
        
    def ensure_directories(self):
        """Ensure required directories exist."""
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metrics_path.mkdir(parents=True, exist_ok=True)

    def start_call_tracking(self, call_id: str) -> CallMetrics:
        """Initialize tracking for a new call."""
        metrics = CallMetrics(call_id)
        self.current_metrics[call_id] = metrics
        return metrics

    def update_speech_metrics(self, call_id: str, audio_segment: AudioSegment):
        """Update speech-related metrics for the call."""
        if call_id not in self.current_metrics:
            return

        metrics = self.current_metrics[call_id]
        
        # Update speech ratios
        if audio_segment.is_speech:
            if audio_segment.speaker_id == "agent":
                metrics.agent_talk_ratio = (
                    (metrics.agent_talk_ratio * metrics.duration + audio_segment.duration) /
                    (metrics.duration + audio_segment.duration)
                )
            elif audio_segment.speaker_id == "client":
                metrics.client_talk_ratio = (
                    (metrics.client_talk_ratio * metrics.duration + audio_segment.duration) /
                    (metrics.duration + audio_segment.duration)
                )
        else:
            metrics.silence_ratio = (
                (metrics.silence_ratio * metrics.duration + audio_segment.duration) /
                (metrics.duration + audio_segment.duration)
            )
        
        metrics.duration += audio_segment.duration
        metrics.speech_ratio = metrics.agent_talk_ratio + metrics.client_talk_ratio

    def update_alm_metrics(self, call_id: str, alm_stage: AlmStage):
        """Update ALM framework completion metrics."""
        if call_id not in self.current_metrics:
            return

        metrics = self.current_metrics[call_id]
        metrics.alm_completion.update({
            "appointment": alm_stage.appointment_progress,
            "location": alm_stage.location_progress,
            "motivation": alm_stage.motivation_progress
        })

    def update_sentiment(self, call_id: str, text: str):
        """Update sentiment metrics for the call."""
        if call_id not in self.current_metrics:
            return

        try:
            from textblob import TextBlob
            if not self.sentiment_analyzer:
                self.sentiment_analyzer = TextBlob
            
            sentiment = self.sentiment_analyzer(text).sentiment.polarity
            metrics = self.current_metrics[call_id]
            metrics.sentiment_scores.append(sentiment)
            
            # Update engagement score based on sentiment
            metrics.engagement_score = np.mean(metrics.sentiment_scores)
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")

    def track_objection_handling(self, call_id: str, objection_type: str, success: bool):
        """Track success rate of objection handling."""
        if call_id not in self.current_metrics:
            return

        metrics = self.current_metrics[call_id]
        metrics.objection_handling_success = (
            metrics.objection_handling_success * 0.7 + (1.0 if success else 0.0) * 0.3
        )

    def record_key_point(self, call_id: str, point: str):
        """Record when a key discussion point is covered."""
        if call_id not in self.current_metrics:
            return

        metrics = self.current_metrics[call_id]
        metrics.key_points_covered.add(point)

    def set_call_outcome(self, call_id: str, appointment_set: bool, follow_up_scheduled: bool):
        """Record the final outcome of the call."""
        if call_id not in self.current_metrics:
            return

        metrics = self.current_metrics[call_id]
        metrics.appointment_set = appointment_set
        metrics.follow_up_scheduled = follow_up_scheduled

    def end_call_tracking(self, call_id: str) -> Dict:
        """Finalize metrics for a call and save them."""
        if call_id not in self.current_metrics:
            return {}

        metrics = self.current_metrics[call_id]
        metrics.end_time = datetime.now()
        
        # Calculate final metrics
        final_metrics = {
            "call_id": metrics.call_id,
            "duration": metrics.duration,
            "start_time": metrics.start_time.isoformat(),
            "end_time": metrics.end_time.isoformat(),
            "speech_metrics": {
                "total_speech_ratio": metrics.speech_ratio,
                "agent_talk_ratio": metrics.agent_talk_ratio,
                "client_talk_ratio": metrics.client_talk_ratio,
                "silence_ratio": metrics.silence_ratio,
                "interruption_count": metrics.interruption_count
            },
            "alm_completion": metrics.alm_completion,
            "engagement": {
                "score": metrics.engagement_score,
                "average_sentiment": np.mean(metrics.sentiment_scores) if metrics.sentiment_scores else 0.0,
                "sentiment_variance": np.var(metrics.sentiment_scores) if metrics.sentiment_scores else 0.0
            },
            "outcomes": {
                "appointment_set": metrics.appointment_set,
                "follow_up_scheduled": metrics.follow_up_scheduled,
                "key_points_covered": list(metrics.key_points_covered),
                "objection_handling_success": metrics.objection_handling_success
            }
        }

        # Save metrics to file
        self._save_metrics(call_id, final_metrics)
        
        # Clean up
        del self.current_metrics[call_id]
        
        return final_metrics

    def _save_metrics(self, call_id: str, metrics: Dict):
        """Save call metrics to a JSON file."""
        try:
            file_path = self.metrics_path / f"{call_id}.json"
            with open(file_path, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics for call {call_id}: {e}")

    def get_call_metrics(self, call_id: str) -> Optional[Dict]:
        """Retrieve metrics for a specific call."""
        try:
            file_path = self.metrics_path / f"{call_id}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading metrics for call {call_id}: {e}")
        return None

    def get_aggregate_metrics(self, start_date: datetime, end_date: datetime) -> Dict:
        """Get aggregate metrics for all calls in a date range."""
        try:
            aggregate_metrics = {
                "total_calls": 0,
                "total_duration": 0,
                "appointment_success_rate": 0,
                "follow_up_rate": 0,
                "average_engagement": 0,
                "average_alm_completion": {
                    "appointment": 0,
                    "location": 0,
                    "motivation": 0
                },
                "average_talk_ratios": {
                    "agent": 0,
                    "client": 0,
                    "silence": 0
                }
            }

            metrics_files = list(self.metrics_path.glob("*.json"))
            valid_calls = []

            for file_path in metrics_files:
                try:
                    with open(file_path, 'r') as f:
                        metrics = json.load(f)
                    
                    call_date = datetime.fromisoformat(metrics["start_time"])
                    if start_date <= call_date <= end_date:
                        valid_calls.append(metrics)
                except Exception as e:
                    logger.error(f"Error processing metrics file {file_path}: {e}")
                    continue

            if not valid_calls:
                return aggregate_metrics

            # Calculate aggregates
            n_calls = len(valid_calls)
            aggregate_metrics["total_calls"] = n_calls
            
            for metrics in valid_calls:
                aggregate_metrics["total_duration"] += metrics["duration"]
                aggregate_metrics["appointment_success_rate"] += int(metrics["outcomes"]["appointment_set"])
                aggregate_metrics["follow_up_rate"] += int(metrics["outcomes"]["follow_up_scheduled"])
                aggregate_metrics["average_engagement"] += metrics["engagement"]["score"]
                
                # ALM completion
                for key in ["appointment", "location", "motivation"]:
                    aggregate_metrics["average_alm_completion"][key] += metrics["alm_completion"][key]
                
                # Talk ratios
                aggregate_metrics["average_talk_ratios"]["agent"] += metrics["speech_metrics"]["agent_talk_ratio"]
                aggregate_metrics["average_talk_ratios"]["client"] += metrics["speech_metrics"]["client_talk_ratio"]
                aggregate_metrics["average_talk_ratios"]["silence"] += metrics["speech_metrics"]["silence_ratio"]

            # Calculate averages
            aggregate_metrics["appointment_success_rate"] /= n_calls
            aggregate_metrics["follow_up_rate"] /= n_calls
            aggregate_metrics["average_engagement"] /= n_calls
            
            for key in aggregate_metrics["average_alm_completion"]:
                aggregate_metrics["average_alm_completion"][key] /= n_calls
            
            for key in aggregate_metrics["average_talk_ratios"]:
                aggregate_metrics["average_talk_ratios"][key] /= n_calls

            return aggregate_metrics

        except Exception as e:
            logger.error(f"Error calculating aggregate metrics: {e}")
            return None

call_analytics = CallAnalytics()
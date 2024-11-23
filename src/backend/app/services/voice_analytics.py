from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import signal
from pydantic import BaseModel
from datetime import datetime
import logging
import librosa
import json

logger = logging.getLogger(__name__)

class VoiceMetrics(BaseModel):
    speaking_rate: float  # words per minute
    pitch_mean: float
    pitch_variance: float
    intensity: float
    pause_ratio: float
    emotion_scores: Dict[str, float]
    timestamp: datetime

class VoiceTurn(BaseModel):
    speaker_id: str
    start_time: float
    end_time: float
    duration: float
    text: str
    metrics: Optional[VoiceMetrics]

class ConversationDynamics(BaseModel):
    turn_taking_balance: float  # ratio of agent to client talk time
    interruption_count: int
    silence_ratio: float
    engagement_score: float
    timestamp: datetime

class VoiceAnalytics:
    def __init__(self):
        self.sample_rate = 16000
        self.frame_length = 512
        self.hop_length = 128
        self.silence_threshold = 0.1
        self.min_silence_duration = 0.5  # seconds
        
        # Emotion detection thresholds
        self.emotion_features = {
            "pitch_range": {"positive": (100, 300), "negative": (50, 150)},
            "intensity_range": {"positive": (0.6, 1.0), "negative": (0.2, 0.5)},
            "speaking_rate": {"positive": (150, 200), "negative": (100, 140)}
        }

    def analyze_voice_metrics(self, audio_array: np.ndarray) -> VoiceMetrics:
        """Analyze voice characteristics from audio segment."""
        try:
            # Calculate pitch
            pitches, magnitudes = librosa.piptrack(
                y=audio_array,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            
            # Get pitch statistics
            pitch_mean = np.mean(pitches[magnitudes > 0])
            pitch_variance = np.var(pitches[magnitudes > 0])
            
            # Calculate intensity
            intensity = np.mean(np.abs(audio_array))
            
            # Estimate speaking rate
            # Simple word count estimation based on energy peaks
            energy = librosa.feature.rms(y=audio_array, hop_length=self.hop_length)[0]
            peaks = signal.find_peaks(energy, distance=int(self.sample_rate/2))[0]
            duration = len(audio_array) / self.sample_rate
            speaking_rate = len(peaks) * (60 / duration)  # words per minute estimation
            
            # Calculate pause ratio
            silence_mask = energy < self.silence_threshold
            pause_ratio = np.sum(silence_mask) / len(energy)
            
            # Emotion analysis based on acoustic features
            emotion_scores = self._analyze_emotions(
                pitch_mean, intensity, speaking_rate
            )
            
            return VoiceMetrics(
                speaking_rate=speaking_rate,
                pitch_mean=float(pitch_mean),
                pitch_variance=float(pitch_variance),
                intensity=float(intensity),
                pause_ratio=float(pause_ratio),
                emotion_scores=emotion_scores,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing voice metrics: {e}")
            return None

    def _analyze_emotions(
        self,
        pitch_mean: float,
        intensity: float,
        speaking_rate: float
    ) -> Dict[str, float]:
        """Analyze emotional state based on voice features."""
        emotions = {
            "confident": 0.0,
            "hesitant": 0.0,
            "interested": 0.0,
            "skeptical": 0.0,
            "positive": 0.0,
            "negative": 0.0
        }
        
        # Confidence analysis
        if pitch_mean > 150 and intensity > 0.6:
            emotions["confident"] = min(1.0, intensity * 1.5)
        else:
            emotions["hesitant"] = min(1.0, (1 - intensity) * 1.5)
        
        # Interest analysis
        if speaking_rate > 150 and pitch_mean > 200:
            emotions["interested"] = min(1.0, speaking_rate / 200)
        else:
            emotions["skeptical"] = min(1.0, (1 - speaking_rate/200) * 1.2)
        
        # Overall sentiment
        if all([
            pitch_mean > self.emotion_features["pitch_range"]["positive"][0],
            intensity > self.emotion_features["intensity_range"]["positive"][0],
            speaking_rate > self.emotion_features["speaking_rate"]["positive"][0]
        ]):
            emotions["positive"] = 0.8
        elif all([
            pitch_mean < self.emotion_features["pitch_range"]["negative"][1],
            intensity < self.emotion_features["intensity_range"]["negative"][1],
            speaking_rate < self.emotion_features["speaking_rate"]["negative"][1]
        ]):
            emotions["negative"] = 0.8
            
        return emotions

    def analyze_conversation_dynamics(
        self,
        turns: List[VoiceTurn]
    ) -> ConversationDynamics:
        """Analyze overall conversation dynamics."""
        try:
            # Calculate talk time for each speaker
            agent_time = sum(
                turn.duration for turn in turns 
                if turn.speaker_id == "agent"
            )
            client_time = sum(
                turn.duration for turn in turns 
                if turn.speaker_id == "client"
            )
            
            # Calculate turn-taking balance
            total_time = agent_time + client_time
            if total_time > 0:
                turn_taking_balance = agent_time / total_time
            else:
                turn_taking_balance = 0.5
            
            # Count interruptions
            interruption_count = 0
            for i in range(len(turns) - 1):
                if turns[i].end_time > turns[i + 1].start_time:
                    interruption_count += 1
            
            # Calculate silence ratio
            conversation_duration = turns[-1].end_time - turns[0].start_time
            speech_time = sum(turn.duration for turn in turns)
            silence_ratio = max(0, (conversation_duration - speech_time) / conversation_duration)
            
            # Calculate engagement score
            engagement_factors = [
                1 - abs(0.5 - turn_taking_balance),  # balanced conversation = higher score
                1 - min(1, interruption_count / 5),  # fewer interruptions = higher score
                1 - silence_ratio,  # less silence = higher score
            ]
            engagement_score = sum(engagement_factors) / len(engagement_factors)
            
            return ConversationDynamics(
                turn_taking_balance=turn_taking_balance,
                interruption_count=interruption_count,
                silence_ratio=silence_ratio,
                engagement_score=engagement_score,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error analyzing conversation dynamics: {e}")
            return None

    def get_conversation_insights(
        self,
        dynamics: ConversationDynamics,
        turns: List[VoiceTurn]
    ) -> List[str]:
        """Generate actionable insights from conversation analysis."""
        insights = []
        
        # Analyze turn-taking balance
        if dynamics.turn_taking_balance > 0.7:
            insights.append(
                "Consider giving the client more opportunity to speak - aim for a 40/60 agent/client ratio"
            )
        elif dynamics.turn_taking_balance < 0.3:
            insights.append(
                "Try to engage more actively in the conversation with strategic questions"
            )
        
        # Analyze interruptions
        if dynamics.interruption_count > 3:
            insights.append(
                "Multiple interruptions detected - try to let the client complete their thoughts"
            )
        
        # Analyze silence
        if dynamics.silence_ratio > 0.3:
            insights.append(
                "Consider using more follow-up questions to reduce silence gaps"
            )
        
        # Analyze emotion trends
        client_emotions = [
            turn.metrics.emotion_scores
            for turn in turns
            if turn.speaker_id == "client" and turn.metrics
        ]
        
        if client_emotions:
            avg_interest = np.mean([e["interested"] for e in client_emotions])
            avg_skepticism = np.mean([e["skeptical"] for e in client_emotions])
            
            if avg_interest < 0.4:
                insights.append(
                    "Client interest seems low - try sharing unique property features or market insights"
                )
            if avg_skepticism > 0.6:
                insights.append(
                    "Client appears skeptical - focus on building trust and providing concrete data"
                )
        
        return insights

    def get_real_time_suggestions(
        self,
        current_metrics: VoiceMetrics,
        conversation_dynamics: ConversationDynamics
    ) -> List[str]:
        """Generate real-time suggestions based on voice analytics."""
        suggestions = []
        
        # Analyze current engagement
        if conversation_dynamics.engagement_score < 0.5:
            suggestions.append(
                "Engagement is low - try asking open-ended questions about their home preferences"
            )
        
        # Analyze emotional state
        if current_metrics.emotion_scores["hesitant"] > 0.7:
            suggestions.append(
                "Client seems hesitant - acknowledge concerns and provide market data"
            )
        elif current_metrics.emotion_scores["interested"] > 0.7:
            suggestions.append(
                "High interest detected - consider moving towards scheduling a viewing"
            )
        
        # Analyze speaking patterns
        if current_metrics.speaking_rate > 180:
            suggestions.append(
                "Consider slowing down to maintain clarity and build trust"
            )
        elif current_metrics.speaking_rate < 120:
            suggestions.append(
                "Try to maintain an engaging pace while remaining clear"
            )
        
        return suggestions

voice_analytics = VoiceAnalytics()
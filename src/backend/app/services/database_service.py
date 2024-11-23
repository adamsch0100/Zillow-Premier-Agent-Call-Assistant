from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.models import Call, Transcript, TranscriptAnalysis, CallMetrics, ActionItem, Script
from models.database import SessionLocal

class DatabaseService:
    def __init__(self):
        self.db: Session = SessionLocal()

    def __del__(self):
        self.db.close()

    # Call-related operations
    async def create_call(self, agent_id: str, lead_phone: str, lead_name: Optional[str] = None) -> Call:
        call = Call(
            agent_id=agent_id,
            lead_phone=lead_phone,
            lead_name=lead_name,
            call_status="active"
        )
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return call

    async def end_call(self, call_id: int, success_rating: Optional[float] = None) -> Call:
        call = self.db.query(Call).filter(Call.id == call_id).first()
        if call:
            call.end_time = datetime.utcnow()
            call.call_status = "completed"
            call.success_rating = success_rating
            call.call_duration = int((call.end_time - call.start_time).total_seconds())
            self.db.commit()
            self.db.refresh(call)
        return call

    async def get_call(self, call_id: int) -> Optional[Call]:
        return self.db.query(Call).filter(Call.id == call_id).first()

    async def get_agent_calls(self, agent_id: str, limit: int = 10) -> List[Call]:
        return self.db.query(Call)\
            .filter(Call.agent_id == agent_id)\
            .order_by(desc(Call.start_time))\
            .limit(limit)\
            .all()

    # Transcript operations
    async def add_transcript(self, call_id: int, text: str, speaker: str, confidence: float) -> Transcript:
        transcript = Transcript(
            call_id=call_id,
            text=text,
            speaker=speaker,
            confidence=confidence
        )
        self.db.add(transcript)
        self.db.commit()
        self.db.refresh(transcript)
        return transcript

    async def get_call_transcripts(self, call_id: int) -> List[Transcript]:
        return self.db.query(Transcript)\
            .filter(Transcript.call_id == call_id)\
            .order_by(Transcript.timestamp)\
            .all()

    # Transcript Analysis operations
    async def add_transcript_analysis(
        self,
        transcript_id: int,
        sentiment_score: float,
        intent: str,
        entities: Dict,
        key_points: Dict
    ) -> TranscriptAnalysis:
        analysis = TranscriptAnalysis(
            transcript_id=transcript_id,
            sentiment_score=sentiment_score,
            intent=intent,
            entities=entities,
            key_points=key_points
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    # Call Metrics operations
    async def create_or_update_metrics(self, call_id: int, metrics_data: Dict) -> CallMetrics:
        metrics = self.db.query(CallMetrics).filter(CallMetrics.call_id == call_id).first()
        if not metrics:
            metrics = CallMetrics(call_id=call_id)
            self.db.add(metrics)

        for key, value in metrics_data.items():
            if hasattr(metrics, key):
                setattr(metrics, key, value)

        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    # Action Items operations
    async def add_action_item(
        self,
        call_id: int,
        description: str,
        priority: str,
        action_type: str
    ) -> ActionItem:
        action = ActionItem(
            call_id=call_id,
            description=description,
            priority=priority,
            status="pending",
            action_type=action_type
        )
        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)
        return action

    async def complete_action_item(self, action_id: int) -> Optional[ActionItem]:
        action = self.db.query(ActionItem).filter(ActionItem.id == action_id).first()
        if action:
            action.status = "completed"
            action.completed_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(action)
        return action

    async def get_pending_actions(self, call_id: int) -> List[ActionItem]:
        return self.db.query(ActionItem)\
            .filter(ActionItem.call_id == call_id, ActionItem.status == "pending")\
            .order_by(desc(ActionItem.created_at))\
            .all()

    # Script operations
    async def add_script(
        self,
        category: str,
        text: str,
        trigger_words: List[str],
        context: Dict,
        variations: List[str]
    ) -> Script:
        script = Script(
            category=category,
            text=text,
            trigger_words=trigger_words,
            context=context,
            variations=variations
        )
        self.db.add(script)
        self.db.commit()
        self.db.refresh(script)
        return script

    async def get_scripts_by_category(self, category: str) -> List[Script]:
        return self.db.query(Script)\
            .filter(Script.category == category)\
            .all()

    async def update_script_usage(self, script_id: int, success: bool = True) -> Script:
        script = self.db.query(Script).filter(Script.id == script_id).first()
        if script:
            script.usage_count += 1
            script.last_used = datetime.utcnow()
            if success:
                # Update success rate using weighted average
                script.success_rate = (
                    (script.success_rate * (script.usage_count - 1) + 1) / script.usage_count
                )
            else:
                script.success_rate = (
                    script.success_rate * (script.usage_count - 1) / script.usage_count
                )
            self.db.commit()
            self.db.refresh(script)
        return script

# Create a singleton instance
db_service = DatabaseService()
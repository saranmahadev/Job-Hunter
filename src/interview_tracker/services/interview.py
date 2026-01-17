"""Interview service for managing interview records."""

from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session, joinedload

from ..core.models import Interview, Pipeline, InterviewQuestion
from ..core.schemas import InterviewCreate, InterviewUpdate
from ..core.enums import (
    PipelineStage, InterviewOutcome, PrepStatus, InterviewMode
)
from ..data.database import get_db


def _get_sync_manager():
    """Lazy import to avoid circular imports."""
    from ..integrations.sync_manager import get_sync_manager
    return get_sync_manager()


class InterviewService:
    """Service for managing interviews."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_db().get_session()
        return self._session

    def create(self, data: InterviewCreate) -> Interview:
        """Create a new interview."""
        interview = Interview(
            pipeline_id=data.pipeline_id,
            stage=data.stage.value,
            round_number=data.round_number,
            scheduled_date=data.scheduled_date,
            duration_minutes=data.duration_minutes,
            mode=data.mode.value,
            meeting_link=data.meeting_link,
            interviewer_name=data.interviewer_name,
            interviewer_title=data.interviewer_title,
            interviewer_linkedin=data.interviewer_linkedin,
            prep_notes=data.prep_notes,
        )

        if data.topics:
            interview.topics = data.topics
        if data.projects_to_pitch:
            interview.projects_to_pitch = data.projects_to_pitch

        self.session.add(interview)

        # Update pipeline's updated_at
        pipeline = self.session.get(Pipeline, data.pipeline_id)
        if pipeline:
            pipeline.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(interview)

        # Sync to Google Sheets and Calendar if online
        try:
            sync_manager = _get_sync_manager()
            sync_manager.sync_interview(interview, pipeline)
        except Exception:
            pass  # Don't fail local operations if sync fails

        return interview

    def get(self, interview_id: int) -> Optional[Interview]:
        """Get an interview by ID."""
        return self.session.get(Interview, interview_id)

    def get_with_pipeline(self, interview_id: int) -> Optional[Interview]:
        """Get an interview with its pipeline loaded."""
        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(Interview.id == interview_id)
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def get_by_pipeline(self, pipeline_id: int) -> List[Interview]:
        """Get all interviews for a pipeline."""
        stmt = (
            select(Interview)
            .where(Interview.pipeline_id == pipeline_id)
            .order_by(Interview.scheduled_date.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_upcoming(self, days_ahead: int = 7) -> List[Interview]:
        """Get upcoming interviews within the specified number of days."""
        now = datetime.utcnow()
        future = now + timedelta(days=days_ahead)

        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(
                and_(
                    Interview.scheduled_date >= now,
                    Interview.scheduled_date <= future,
                    Interview.outcome == InterviewOutcome.PENDING.value,
                )
            )
            .order_by(Interview.scheduled_date.asc())
        )
        return list(self.session.execute(stmt).unique().scalars().all())

    def get_all_upcoming(self) -> List[Interview]:
        """Get all upcoming interviews."""
        now = datetime.utcnow()

        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(
                and_(
                    Interview.scheduled_date >= now,
                    Interview.outcome == InterviewOutcome.PENDING.value,
                )
            )
            .order_by(Interview.scheduled_date.asc())
        )
        return list(self.session.execute(stmt).unique().scalars().all())

    def get_pending_outcomes(self) -> List[Interview]:
        """Get interviews that are done but have pending outcomes."""
        now = datetime.utcnow()

        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(
                and_(
                    Interview.scheduled_date < now,
                    Interview.outcome == InterviewOutcome.PENDING.value,
                )
            )
            .order_by(Interview.scheduled_date.desc())
        )
        return list(self.session.execute(stmt).unique().scalars().all())

    def update(self, interview_id: int, data: InterviewUpdate) -> Optional[Interview]:
        """Update an interview."""
        interview = self.get(interview_id)
        if not interview:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle enum conversions
        enum_fields = {
            'stage': PipelineStage,
            'mode': InterviewMode,
            'prep_status': PrepStatus,
            'outcome': InterviewOutcome,
        }

        for field, enum_class in enum_fields.items():
            if field in update_data and update_data[field] is not None:
                value = update_data[field]
                if isinstance(value, enum_class):
                    update_data[field] = value.value

        # Handle list fields
        if 'topics' in update_data:
            interview.topics = update_data.pop('topics')
        if 'projects_to_pitch' in update_data:
            interview.projects_to_pitch = update_data.pop('projects_to_pitch')

        for field, value in update_data.items():
            setattr(interview, field, value)

        # If outcome is set and not pending, set completed_at
        if (
            interview.outcome != InterviewOutcome.PENDING.value
            and interview.completed_at is None
        ):
            interview.completed_at = datetime.utcnow()

        # Update pipeline's updated_at
        pipeline = self.session.get(Pipeline, interview.pipeline_id)
        if pipeline:
            pipeline.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(interview)

        # Sync to Google Sheets and Calendar if online
        try:
            sync_manager = _get_sync_manager()
            pipeline = self.session.get(Pipeline, interview.pipeline_id)
            if pipeline:
                sync_manager.sync_interview(interview, pipeline)
        except Exception:
            pass

        return interview

    def mark_complete(
        self,
        interview_id: int,
        outcome: InterviewOutcome,
        feedback: Optional[str] = None,
        self_assessment: Optional[str] = None,
    ) -> Optional[Interview]:
        """Mark an interview as complete with outcome."""
        interview = self.get(interview_id)
        if not interview:
            return None

        interview.outcome = outcome.value
        interview.completed_at = datetime.utcnow()
        if feedback:
            interview.feedback_received = feedback
        if self_assessment:
            interview.self_assessment = self_assessment

        # Update pipeline
        pipeline = self.session.get(Pipeline, interview.pipeline_id)
        if pipeline:
            pipeline.updated_at = datetime.utcnow()

        self.session.commit()
        self.session.refresh(interview)

        # Sync to Google Sheets and Calendar if online
        try:
            sync_manager = _get_sync_manager()
            if pipeline:
                sync_manager.sync_interview(interview, pipeline)
        except Exception:
            pass

        return interview

    def update_prep_status(
        self,
        interview_id: int,
        status: PrepStatus,
        confidence: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[Interview]:
        """Update preparation status for an interview."""
        interview = self.get(interview_id)
        if not interview:
            return None

        interview.prep_status = status.value
        if confidence is not None:
            interview.confidence = confidence
        if notes is not None:
            interview.prep_notes = notes

        self.session.commit()
        self.session.refresh(interview)
        return interview

    def mark_thank_you_sent(self, interview_id: int) -> Optional[Interview]:
        """Mark that a thank-you note was sent."""
        interview = self.get(interview_id)
        if not interview:
            return None

        interview.thank_you_sent = True
        self.session.commit()
        self.session.refresh(interview)
        return interview

    def delete(self, interview_id: int) -> bool:
        """Delete an interview."""
        interview = self.get(interview_id)
        if not interview:
            return False

        self.session.delete(interview)
        self.session.commit()
        return True

    def get_interviews_needing_prep(self, days_ahead: int = 3) -> List[Interview]:
        """Get upcoming interviews where prep is not complete."""
        now = datetime.utcnow()
        future = now + timedelta(days=days_ahead)

        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(
                and_(
                    Interview.scheduled_date >= now,
                    Interview.scheduled_date <= future,
                    Interview.outcome == InterviewOutcome.PENDING.value,
                    Interview.prep_status != PrepStatus.READY.value,
                )
            )
            .order_by(Interview.scheduled_date.asc())
        )
        return list(self.session.execute(stmt).unique().scalars().all())

    def get_interviews_needing_follow_up(self) -> List[Interview]:
        """Get interviews where thank-you hasn't been sent."""
        yesterday = datetime.utcnow() - timedelta(days=1)

        stmt = (
            select(Interview)
            .options(joinedload(Interview.pipeline))
            .where(
                and_(
                    Interview.scheduled_date < yesterday,
                    Interview.thank_you_sent == False,
                    Interview.outcome != InterviewOutcome.FAILED.value,
                )
            )
            .order_by(Interview.scheduled_date.desc())
        )
        return list(self.session.execute(stmt).unique().scalars().all())

    def close(self):
        """Close the session if we own it."""
        if self._session:
            self._session.close()
            self._session = None

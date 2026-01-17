"""Pipeline service for managing job application pipelines."""

from datetime import datetime, date, timedelta
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from ..core.models import Pipeline, Interview
from ..core.schemas import PipelineCreate, PipelineUpdate, PipelineRead
from ..core.enums import PipelineStage, PipelineHealth, InterviewOutcome
from ..core.state_machine import PipelineStateMachine, TransitionError
from ..data.database import get_db


def _get_sync_manager():
    """Lazy import to avoid circular imports."""
    from ..integrations.sync_manager import get_sync_manager
    return get_sync_manager()


class PipelineService:
    """Service for managing pipelines."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_db().get_session()
        return self._session

    def create(self, data: PipelineCreate) -> Pipeline:
        """Create a new pipeline."""
        pipeline = Pipeline(
            company=data.company,
            role=data.role,
            job_url=data.job_url,
            applied_date=data.applied_date,
            salary_range=data.salary_range,
            location=data.location,
            remote_policy=data.remote_policy,
            notes=data.notes,
            priority=data.priority,
        )
        self.session.add(pipeline)
        self.session.commit()
        self.session.refresh(pipeline)

        # Sync to Google Sheets if online
        try:
            sync_manager = _get_sync_manager()
            sync_manager.sync_pipeline(pipeline)
        except Exception:
            pass  # Don't fail local operations if sync fails

        return pipeline

    def get(self, pipeline_id: int) -> Optional[Pipeline]:
        """Get a pipeline by ID."""
        return self.session.get(Pipeline, pipeline_id)

    def get_with_interviews(self, pipeline_id: int) -> Optional[Pipeline]:
        """Get a pipeline with its interviews loaded."""
        stmt = (
            select(Pipeline)
            .options(joinedload(Pipeline.interviews))
            .where(Pipeline.id == pipeline_id)
        )
        return self.session.execute(stmt).unique().scalar_one_or_none()

    def get_all(self, include_closed: bool = False) -> List[Pipeline]:
        """Get all pipelines, optionally including closed ones."""
        stmt = select(Pipeline).order_by(Pipeline.updated_at.desc())

        if not include_closed:
            stmt = stmt.where(
                Pipeline.current_stage.notin_([
                    PipelineStage.REJECTED.value,
                    PipelineStage.DROPPED.value,
                ])
            )

        return list(self.session.execute(stmt).scalars().all())

    def get_active(self) -> List[Pipeline]:
        """Get only active (non-terminal) pipelines."""
        stmt = (
            select(Pipeline)
            .where(
                Pipeline.current_stage.notin_([
                    PipelineStage.REJECTED.value,
                    PipelineStage.DROPPED.value,
                    PipelineStage.OFFER.value,
                ])
            )
            .order_by(Pipeline.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update(self, pipeline_id: int, data: PipelineUpdate) -> Optional[Pipeline]:
        """Update a pipeline."""
        pipeline = self.get(pipeline_id)
        if not pipeline:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle stage transition with validation
        if 'current_stage' in update_data:
            new_stage = update_data['current_stage']
            if isinstance(new_stage, PipelineStage):
                new_stage = new_stage.value
            update_data['current_stage'] = new_stage

        for field, value in update_data.items():
            setattr(pipeline, field, value)

        pipeline.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(pipeline)

        # Sync to Google Sheets if online
        try:
            sync_manager = _get_sync_manager()
            sync_manager.sync_pipeline(pipeline)
        except Exception:
            pass

        return pipeline

    def advance_stage(
        self, pipeline_id: int, new_stage: PipelineStage
    ) -> Pipeline:
        """
        Advance a pipeline to a new stage with validation.

        Raises:
            TransitionError: If the transition is not valid.
            ValueError: If pipeline not found.
        """
        pipeline = self.get(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        current_stage = PipelineStage(pipeline.current_stage)
        is_valid, error_msg = PipelineStateMachine.validate_transition(
            current_stage, new_stage
        )

        if not is_valid:
            raise TransitionError(current_stage, new_stage, error_msg)

        pipeline.current_stage = new_stage.value
        pipeline.updated_at = datetime.utcnow()
        self.session.commit()
        self.session.refresh(pipeline)

        # Sync to Google Sheets if online
        try:
            sync_manager = _get_sync_manager()
            sync_manager.sync_pipeline(pipeline)
        except Exception:
            pass

        return pipeline

    def delete(self, pipeline_id: int) -> bool:
        """Delete a pipeline and all related data."""
        pipeline = self.get(pipeline_id)
        if not pipeline:
            return False

        self.session.delete(pipeline)
        self.session.commit()
        return True

    def calculate_health(self, pipeline: Pipeline) -> PipelineHealth:
        """Calculate the health status of a pipeline."""
        stage = PipelineStage(pipeline.current_stage)

        # Terminal states
        if PipelineStateMachine.is_terminal(stage):
            return PipelineHealth.CLOSED

        days_since_update = (datetime.utcnow() - pipeline.updated_at).days

        # Check for upcoming interviews
        upcoming_interviews = [
            i for i in pipeline.interviews
            if i.scheduled_date and i.scheduled_date > datetime.utcnow()
        ]
        if upcoming_interviews:
            return PipelineHealth.ACTIVE

        # Check for pending outcomes (interview done, waiting for result)
        pending_interviews = [
            i for i in pipeline.interviews
            if i.outcome == InterviewOutcome.PENDING.value
            and i.scheduled_date
            and i.scheduled_date < datetime.utcnow()
        ]

        if pending_interviews:
            oldest = min(i.scheduled_date for i in pending_interviews)
            days_waiting = (datetime.utcnow() - oldest).days
            if days_waiting > 5:
                return PipelineHealth.NEEDS_FOLLOWUP
            return PipelineHealth.AWAITING

        # Check for staleness
        if days_since_update > 10:
            return PipelineHealth.STALE
        elif days_since_update > 5:
            return PipelineHealth.NEEDS_FOLLOWUP

        return PipelineHealth.ACTIVE

    def get_pipelines_needing_attention(self) -> List[tuple[Pipeline, PipelineHealth, str]]:
        """Get pipelines that need user attention with reasons."""
        pipelines = self.get_active()
        attention_needed = []

        for pipeline in pipelines:
            health = self.calculate_health(pipeline)

            if health == PipelineHealth.NEEDS_FOLLOWUP:
                attention_needed.append((
                    pipeline,
                    health,
                    f"No activity for {pipeline.days_since_update} days"
                ))
            elif health == PipelineHealth.STALE:
                attention_needed.append((
                    pipeline,
                    health,
                    f"Stale - no updates for {pipeline.days_since_update} days"
                ))
            elif health == PipelineHealth.AWAITING:
                # Check if waiting too long
                pending = [
                    i for i in pipeline.interviews
                    if i.outcome == InterviewOutcome.PENDING.value
                    and i.scheduled_date
                    and i.scheduled_date < datetime.utcnow()
                ]
                if pending:
                    oldest = min(i.scheduled_date for i in pending)
                    days = (datetime.utcnow() - oldest).days
                    if days > 3:
                        attention_needed.append((
                            pipeline,
                            health,
                            f"Awaiting response for {days} days"
                        ))

        return attention_needed

    def get_stage_distribution(self) -> dict[str, int]:
        """Get count of pipelines in each stage."""
        stmt = (
            select(Pipeline.current_stage, func.count(Pipeline.id))
            .group_by(Pipeline.current_stage)
        )
        results = self.session.execute(stmt).all()
        return {stage: count for stage, count in results}

    def search(self, query: str) -> List[Pipeline]:
        """Search pipelines by company or role name."""
        search_term = f"%{query}%"
        stmt = (
            select(Pipeline)
            .where(
                (Pipeline.company.ilike(search_term)) |
                (Pipeline.role.ilike(search_term))
            )
            .order_by(Pipeline.updated_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def close(self):
        """Close the session if we own it."""
        if self._session:
            self._session.close()
            self._session = None

"""Metrics service for dashboard calculations."""

from datetime import datetime, date, timedelta
from typing import List, Optional
from collections import Counter

from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from ..core.models import Pipeline, Interview
from ..core.schemas import DashboardMetrics, UpcomingInterview, PipelineAttention
from ..core.enums import PipelineStage, InterviewOutcome, PipelineHealth
from ..data.database import get_db
from .pipeline import PipelineService


class MetricsService:
    """Service for calculating dashboard metrics."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_db().get_session()
        return self._session

    def get_dashboard_metrics(self) -> DashboardMetrics:
        """Calculate all dashboard metrics."""
        return DashboardMetrics(
            total_active_pipelines=self._count_active_pipelines(),
            total_interviews_completed=self._count_completed_interviews(),
            interviews_this_week=self._count_interviews_this_week(),
            pass_rate=self._calculate_pass_rate(),
            average_confidence=self._calculate_avg_confidence(),
            pending_follow_ups=self._count_pending_follow_ups(),
            offers_received=self._count_offers(),
            rejections=self._count_rejections(),
            avg_days_in_pipeline=self._calculate_avg_days_in_pipeline(),
            stage_distribution=self._get_stage_distribution(),
        )

    def _count_active_pipelines(self) -> int:
        """Count pipelines that are not in terminal states."""
        stmt = (
            select(func.count(Pipeline.id))
            .where(
                Pipeline.current_stage.notin_([
                    PipelineStage.REJECTED.value,
                    PipelineStage.DROPPED.value,
                    PipelineStage.OFFER.value,
                ])
            )
        )
        return self.session.execute(stmt).scalar() or 0

    def _count_completed_interviews(self) -> int:
        """Count interviews with pass or fail outcomes."""
        stmt = (
            select(func.count(Interview.id))
            .where(
                Interview.outcome.in_([
                    InterviewOutcome.PASSED.value,
                    InterviewOutcome.FAILED.value,
                ])
            )
        )
        return self.session.execute(stmt).scalar() or 0

    def _count_interviews_this_week(self) -> int:
        """Count interviews scheduled for this week."""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        stmt = (
            select(func.count(Interview.id))
            .where(
                and_(
                    Interview.scheduled_date >= datetime.combine(start_of_week, datetime.min.time()),
                    Interview.scheduled_date <= datetime.combine(end_of_week, datetime.max.time()),
                )
            )
        )
        return self.session.execute(stmt).scalar() or 0

    def _calculate_pass_rate(self) -> float:
        """Calculate the overall pass rate percentage."""
        stmt = (
            select(Interview.outcome, func.count(Interview.id))
            .where(
                Interview.outcome.in_([
                    InterviewOutcome.PASSED.value,
                    InterviewOutcome.FAILED.value,
                ])
            )
            .group_by(Interview.outcome)
        )
        results = dict(self.session.execute(stmt).all())

        passed = results.get(InterviewOutcome.PASSED.value, 0)
        failed = results.get(InterviewOutcome.FAILED.value, 0)
        total = passed + failed

        if total == 0:
            return 0.0
        return round((passed / total) * 100, 1)

    def _calculate_avg_confidence(self) -> float:
        """Calculate average confidence level across all interviews."""
        stmt = (
            select(func.avg(Interview.confidence))
            .where(Interview.confidence.isnot(None))
        )
        result = self.session.execute(stmt).scalar()
        return round(result, 2) if result else 0.0

    def _count_pending_follow_ups(self) -> int:
        """Count pipelines needing follow-up action."""
        pipeline_service = PipelineService(self.session)
        attention_list = pipeline_service.get_pipelines_needing_attention()
        return len([
            p for p, health, _ in attention_list
            if health in [PipelineHealth.NEEDS_FOLLOWUP, PipelineHealth.STALE]
        ])

    def _count_offers(self) -> int:
        """Count pipelines that resulted in offers."""
        stmt = (
            select(func.count(Pipeline.id))
            .where(Pipeline.current_stage == PipelineStage.OFFER.value)
        )
        return self.session.execute(stmt).scalar() or 0

    def _count_rejections(self) -> int:
        """Count pipelines that resulted in rejections."""
        stmt = (
            select(func.count(Pipeline.id))
            .where(Pipeline.current_stage == PipelineStage.REJECTED.value)
        )
        return self.session.execute(stmt).scalar() or 0

    def _calculate_avg_days_in_pipeline(self) -> float:
        """Calculate average days from application to outcome."""
        stmt = (
            select(Pipeline)
            .where(
                Pipeline.current_stage.in_([
                    PipelineStage.OFFER.value,
                    PipelineStage.REJECTED.value,
                    PipelineStage.DROPPED.value,
                ])
            )
        )
        completed_pipelines = self.session.execute(stmt).scalars().all()

        if not completed_pipelines:
            return 0.0

        total_days = sum(
            (p.updated_at.date() - p.applied_date).days
            for p in completed_pipelines
        )
        return round(total_days / len(completed_pipelines), 1)

    def _get_stage_distribution(self) -> dict[str, int]:
        """Get count of active pipelines by stage."""
        stmt = (
            select(Pipeline.current_stage, func.count(Pipeline.id))
            .where(
                Pipeline.current_stage.notin_([
                    PipelineStage.REJECTED.value,
                    PipelineStage.DROPPED.value,
                ])
            )
            .group_by(Pipeline.current_stage)
        )
        results = self.session.execute(stmt).all()
        return {stage: count for stage, count in results}

    def get_upcoming_interviews(self, limit: int = 5) -> List[UpcomingInterview]:
        """Get the next upcoming interviews for dashboard display."""
        now = datetime.utcnow()

        stmt = (
            select(Interview, Pipeline)
            .join(Pipeline)
            .where(
                and_(
                    Interview.scheduled_date >= now,
                    Interview.outcome == InterviewOutcome.PENDING.value,
                )
            )
            .order_by(Interview.scheduled_date.asc())
            .limit(limit)
        )

        results = self.session.execute(stmt).all()
        upcoming = []

        for interview, pipeline in results:
            days_until = (interview.scheduled_date.date() - date.today()).days
            upcoming.append(UpcomingInterview(
                id=interview.id,
                company=pipeline.company,
                role=pipeline.role,
                stage=interview.stage,
                scheduled_date=interview.scheduled_date,
                prep_status=interview.prep_status,
                days_until=days_until,
            ))

        return upcoming

    def get_pipelines_needing_attention(self, limit: int = 5) -> List[PipelineAttention]:
        """Get pipelines that need attention for dashboard display."""
        pipeline_service = PipelineService(self.session)
        attention_list = pipeline_service.get_pipelines_needing_attention()

        result = []
        for pipeline, health, reason in attention_list[:limit]:
            result.append(PipelineAttention(
                id=pipeline.id,
                company=pipeline.company,
                role=pipeline.role,
                current_stage=pipeline.current_stage,
                health=health,
                days_since_update=pipeline.days_since_update,
                reason=reason,
            ))

        return result

    def get_weekly_summary(self) -> dict:
        """Get a summary of activity for the current week."""
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())

        # Interviews this week
        interviews_stmt = (
            select(func.count(Interview.id))
            .where(
                Interview.scheduled_date >= datetime.combine(
                    start_of_week, datetime.min.time()
                )
            )
        )
        interviews_count = self.session.execute(interviews_stmt).scalar() or 0

        # New pipelines this week
        pipelines_stmt = (
            select(func.count(Pipeline.id))
            .where(Pipeline.created_at >= datetime.combine(
                start_of_week, datetime.min.time()
            ))
        )
        new_pipelines = self.session.execute(pipelines_stmt).scalar() or 0

        # Outcomes this week
        outcomes_stmt = (
            select(Interview.outcome, func.count(Interview.id))
            .where(
                and_(
                    Interview.completed_at >= datetime.combine(
                        start_of_week, datetime.min.time()
                    ),
                    Interview.outcome.in_([
                        InterviewOutcome.PASSED.value,
                        InterviewOutcome.FAILED.value,
                    ])
                )
            )
            .group_by(Interview.outcome)
        )
        outcomes = dict(self.session.execute(outcomes_stmt).all())

        return {
            'interviews_scheduled': interviews_count,
            'new_applications': new_pipelines,
            'interviews_passed': outcomes.get(InterviewOutcome.PASSED.value, 0),
            'interviews_failed': outcomes.get(InterviewOutcome.FAILED.value, 0),
            'week_start': start_of_week.isoformat(),
        }

    def close(self):
        """Close the session if we own it."""
        if self._session:
            self._session.close()
            self._session = None

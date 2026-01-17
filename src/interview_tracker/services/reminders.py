"""Reminder service for notifications and alerts."""

import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable
import logging

from ..core.models import Interview, Pipeline
from ..core.enums import InterviewOutcome, PrepStatus, PipelineHealth
from ..data.database import get_db
from .interview import InterviewService
from .pipeline import PipelineService

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing reminders and notifications."""

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[str, str], None]] = []
        self._check_interval = 300  # 5 minutes

    def register_callback(self, callback: Callable[[str, str], None]):
        """
        Register a callback to be called when a reminder is triggered.

        The callback receives (title, message) arguments.
        """
        self._callbacks.append(callback)

    def _notify(self, title: str, message: str):
        """Send notification through all registered callbacks."""
        for callback in self._callbacks:
            try:
                callback(title, message)
            except Exception as e:
                logger.error(f"Error in notification callback: {e}")

        # Also try to send desktop notification
        self._send_desktop_notification(title, message)

    def _send_desktop_notification(self, title: str, message: str):
        """Send a desktop notification using plyer."""
        try:
            from plyer import notification
            notification.notify(
                title=title,
                message=message,
                app_name="Interview Tracker",
                timeout=10,
            )
        except ImportError:
            logger.debug("plyer not available for desktop notifications")
        except Exception as e:
            logger.debug(f"Could not send desktop notification: {e}")

    def check_reminders(self):
        """Check for pending reminders and send notifications."""
        db = get_db()

        with db.session_scope() as session:
            self._check_upcoming_interviews(session)
            self._check_prep_status(session)
            self._check_follow_ups(session)

    def _check_upcoming_interviews(self, session):
        """Check for interviews happening soon."""
        interview_service = InterviewService(session)

        # Interviews in next 24 hours
        upcoming = interview_service.get_upcoming(days_ahead=1)

        for interview in upcoming:
            if not interview.scheduled_date:
                continue

            hours_until = (interview.scheduled_date - datetime.utcnow()).total_seconds() / 3600
            pipeline = interview.pipeline

            if hours_until <= 1 and hours_until > 0:
                self._notify(
                    f"Interview in 1 hour!",
                    f"{pipeline.company} - {interview.interview_stage.display_name}"
                )
            elif hours_until <= 24 and hours_until > 23:
                self._notify(
                    f"Interview tomorrow",
                    f"{pipeline.company} - {interview.interview_stage.display_name} at {interview.scheduled_date.strftime('%H:%M')}"
                )

    def _check_prep_status(self, session):
        """Check for interviews needing preparation."""
        interview_service = InterviewService(session)

        # Interviews in next 2 days where prep is not ready
        needing_prep = interview_service.get_interviews_needing_prep(days_ahead=2)

        for interview in needing_prep:
            if not interview.scheduled_date:
                continue

            hours_until = (interview.scheduled_date - datetime.utcnow()).total_seconds() / 3600
            pipeline = interview.pipeline

            if hours_until <= 24:
                self._notify(
                    "Prep not complete!",
                    f"{pipeline.company} interview in {int(hours_until)} hours - prep status: {interview.preparation_status.display_name}"
                )

    def _check_follow_ups(self, session):
        """Check for pipelines needing follow-up."""
        pipeline_service = PipelineService(session)

        attention_needed = pipeline_service.get_pipelines_needing_attention()

        # Only notify about follow-ups once per day (approximate by checking time)
        current_hour = datetime.now().hour
        if current_hour != 9:  # Only notify at 9 AM
            return

        follow_up_count = len([
            (p, h, r) for p, h, r in attention_needed
            if h == PipelineHealth.NEEDS_FOLLOWUP
        ])

        if follow_up_count > 0:
            self._notify(
                "Follow-ups needed",
                f"You have {follow_up_count} pipeline(s) that need follow-up"
            )

    def start_background_checker(self):
        """Start the background reminder checker thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()
        logger.info("Started background reminder checker")

    def stop_background_checker(self):
        """Stop the background reminder checker."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Stopped background reminder checker")

    def _background_loop(self):
        """Background loop that checks for reminders periodically."""
        while self._running:
            try:
                self.check_reminders()
            except Exception as e:
                logger.error(f"Error checking reminders: {e}")

            # Sleep in small intervals to allow for quick shutdown
            for _ in range(self._check_interval):
                if not self._running:
                    break
                time.sleep(1)


class DailySummary:
    """Generate daily summary of interview activity."""

    @staticmethod
    def generate() -> str:
        """Generate a text summary of today's interview activity."""
        db = get_db()

        with db.session_scope() as session:
            interview_service = InterviewService(session)
            pipeline_service = PipelineService(session)

            # Today's interviews
            today_interviews = interview_service.get_upcoming(days_ahead=0)

            # Pending follow-ups
            attention = pipeline_service.get_pipelines_needing_attention()
            follow_ups = [(p, h, r) for p, h, r in attention if h == PipelineHealth.NEEDS_FOLLOWUP]

            # Build summary
            lines = ["=== Daily Interview Summary ===", ""]

            if today_interviews:
                lines.append(f"Interviews today: {len(today_interviews)}")
                for interview in today_interviews:
                    pipeline = interview.pipeline
                    time_str = interview.scheduled_date.strftime("%H:%M") if interview.scheduled_date else "TBD"
                    lines.append(f"  - {time_str}: {pipeline.company} ({interview.interview_stage.display_name})")
                lines.append("")

            if follow_ups:
                lines.append(f"Follow-ups needed: {len(follow_ups)}")
                for pipeline, health, reason in follow_ups[:5]:
                    lines.append(f"  - {pipeline.company}: {reason}")
                lines.append("")

            # Active pipelines count
            active = pipeline_service.get_active()
            lines.append(f"Active pipelines: {len(active)}")

            return "\n".join(lines)


# Global reminder service instance
_reminder_service: Optional[ReminderService] = None


def get_reminder_service() -> ReminderService:
    """Get the global reminder service instance."""
    global _reminder_service
    if _reminder_service is None:
        _reminder_service = ReminderService()
    return _reminder_service

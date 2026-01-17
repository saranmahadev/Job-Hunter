"""Google Calendar integration for Interview Tracker."""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_auth import get_auth_manager
from ..core.models import Interview, Pipeline
from ..core.enums import InterviewMode

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for syncing interviews with Google Calendar."""

    # Calendar event colors (Google Calendar color IDs)
    COLOR_PENDING = "5"  # Yellow
    COLOR_CONFIRMED = "10"  # Green
    COLOR_PASSED = "2"  # Green
    COLOR_FAILED = "11"  # Red

    def __init__(self, calendar_id: str = "primary"):
        self._calendar_id = calendar_id
        self._service = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to Google Calendar."""
        return self._service is not None

    def connect(self) -> bool:
        """Connect to Google Calendar API."""
        auth_manager = get_auth_manager()
        credentials = auth_manager.get_credentials()

        if not credentials:
            logger.warning("Not authenticated with Google")
            return False

        try:
            self._service = build('calendar', 'v3', credentials=credentials)
            logger.info("Connected to Google Calendar API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Calendar API: {e}")
            return False

    def set_calendar_id(self, calendar_id: str):
        """Set the calendar ID to use (default is 'primary')."""
        self._calendar_id = calendar_id

    def get_calendars(self) -> List[Dict[str, str]]:
        """Get list of available calendars."""
        if not self._service:
            if not self.connect():
                return []

        try:
            calendar_list = self._service.calendarList().list().execute()
            return [
                {
                    'id': cal['id'],
                    'name': cal.get('summary', 'Untitled'),
                    'primary': cal.get('primary', False),
                }
                for cal in calendar_list.get('items', [])
            ]
        except HttpError as e:
            logger.error(f"Failed to get calendars: {e}")
            return []

    def create_interview_event(
        self,
        interview: Interview,
        pipeline: Pipeline,
    ) -> Optional[str]:
        """
        Create a calendar event for an interview.

        Returns:
            The event ID if successful, None otherwise.
        """
        if not self._service:
            if not self.connect():
                return None

        if not interview.scheduled_date:
            logger.warning("Interview has no scheduled date")
            return None

        # Build event description
        description_parts = [
            f"Company: {pipeline.company}",
            f"Role: {pipeline.role}",
            f"Stage: {interview.interview_stage.display_name}",
            f"Round: {interview.round_number}",
            f"Mode: {interview.interview_mode.display_name}",
        ]

        if interview.interviewer_name:
            description_parts.append(f"Interviewer: {interview.interviewer_name}")
            if interview.interviewer_title:
                description_parts[-1] += f" ({interview.interviewer_title})"

        if interview.meeting_link:
            description_parts.append(f"Meeting Link: {interview.meeting_link}")

        if interview.topics:
            description_parts.append(f"\nTopics to Prepare:\n- " + "\n- ".join(interview.topics))

        if interview.prep_notes:
            description_parts.append(f"\nNotes:\n{interview.prep_notes}")

        description = "\n".join(description_parts)

        # Calculate end time
        end_time = interview.scheduled_date + timedelta(minutes=interview.duration_minutes)

        # Build event
        event = {
            'summary': f"Interview: {pipeline.company} - {interview.interview_stage.display_name}",
            'description': description,
            'start': {
                'dateTime': interview.scheduled_date.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 60},
                    {'method': 'popup', 'minutes': 15},
                    {'method': 'email', 'minutes': 1440},  # 24 hours
                ],
            },
            'colorId': self.COLOR_PENDING,
        }

        # Add meeting link as conference data if it looks like a video call link
        if interview.meeting_link:
            if any(domain in interview.meeting_link.lower() for domain in
                   ['zoom.us', 'meet.google', 'teams.microsoft', 'webex']):
                event['conferenceData'] = {
                    'entryPoints': [{
                        'entryPointType': 'video',
                        'uri': interview.meeting_link,
                        'label': 'Join Meeting',
                    }]
                }

        try:
            created_event = self._service.events().insert(
                calendarId=self._calendar_id,
                body=event,
                conferenceDataVersion=1 if 'conferenceData' in event else 0,
            ).execute()

            event_id = created_event.get('id')
            logger.info(f"Created calendar event: {event_id}")
            return event_id

        except HttpError as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def update_interview_event(
        self,
        event_id: str,
        interview: Interview,
        pipeline: Pipeline,
    ) -> bool:
        """Update an existing calendar event."""
        if not self._service:
            if not self.connect():
                return False

        if not interview.scheduled_date:
            return False

        # Build updated description
        description_parts = [
            f"Company: {pipeline.company}",
            f"Role: {pipeline.role}",
            f"Stage: {interview.interview_stage.display_name}",
            f"Round: {interview.round_number}",
            f"Mode: {interview.interview_mode.display_name}",
            f"Prep Status: {interview.preparation_status.display_name}",
            f"Outcome: {interview.interview_outcome.display_name}",
        ]

        if interview.interviewer_name:
            description_parts.append(f"Interviewer: {interview.interviewer_name}")

        if interview.meeting_link:
            description_parts.append(f"Meeting Link: {interview.meeting_link}")

        if interview.topics:
            description_parts.append(f"\nTopics:\n- " + "\n- ".join(interview.topics))

        description = "\n".join(description_parts)

        # Determine color based on outcome
        color_id = self.COLOR_PENDING
        if interview.outcome == "passed":
            color_id = self.COLOR_PASSED
        elif interview.outcome == "failed":
            color_id = self.COLOR_FAILED

        end_time = interview.scheduled_date + timedelta(minutes=interview.duration_minutes)

        event = {
            'summary': f"Interview: {pipeline.company} - {interview.interview_stage.display_name}",
            'description': description,
            'start': {
                'dateTime': interview.scheduled_date.isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': 'UTC',
            },
            'colorId': color_id,
        }

        try:
            self._service.events().update(
                calendarId=self._calendar_id,
                eventId=event_id,
                body=event,
            ).execute()

            logger.info(f"Updated calendar event: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to update calendar event: {e}")
            return False

    def delete_interview_event(self, event_id: str) -> bool:
        """Delete a calendar event."""
        if not self._service:
            if not self.connect():
                return False

        try:
            self._service.events().delete(
                calendarId=self._calendar_id,
                eventId=event_id,
            ).execute()

            logger.info(f"Deleted calendar event: {event_id}")
            return True

        except HttpError as e:
            logger.error(f"Failed to delete calendar event: {e}")
            return False

    def get_upcoming_events(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get upcoming calendar events."""
        if not self._service:
            if not self.connect():
                return []

        now = datetime.utcnow()
        time_max = now + timedelta(days=days_ahead)

        try:
            events_result = self._service.events().list(
                calendarId=self._calendar_id,
                timeMin=now.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=50,
                singleEvents=True,
                orderBy='startTime',
                q='Interview:',  # Search for interview events
            ).execute()

            events = events_result.get('items', [])
            return [
                {
                    'id': event['id'],
                    'summary': event.get('summary', ''),
                    'start': event['start'].get('dateTime', event['start'].get('date')),
                    'end': event['end'].get('dateTime', event['end'].get('date')),
                    'description': event.get('description', ''),
                }
                for event in events
            ]

        except HttpError as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []

    def find_event_by_interview(
        self,
        interview: Interview,
        pipeline: Pipeline,
    ) -> Optional[str]:
        """
        Find an existing calendar event for an interview.

        Returns:
            The event ID if found, None otherwise.
        """
        if not self._service or not interview.scheduled_date:
            return None

        # Search around the scheduled time
        time_min = interview.scheduled_date - timedelta(hours=1)
        time_max = interview.scheduled_date + timedelta(hours=1)

        try:
            events_result = self._service.events().list(
                calendarId=self._calendar_id,
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                singleEvents=True,
                q=f"Interview: {pipeline.company}",
            ).execute()

            events = events_result.get('items', [])
            for event in events:
                if pipeline.company in event.get('summary', ''):
                    return event['id']

            return None

        except HttpError as e:
            logger.error(f"Failed to find event: {e}")
            return None


# Global calendar service instance
_calendar_service: Optional[GoogleCalendarService] = None


def get_calendar_service() -> GoogleCalendarService:
    """Get the global calendar service instance."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service

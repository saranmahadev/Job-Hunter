"""Google Sheets integration for Interview Tracker."""

import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import logging

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .google_auth import get_auth_manager
from ..core.models import Pipeline, Interview, InterviewQuestion, Contact
from ..core.enums import PipelineStage, InterviewMode, InterviewOutcome, PrepStatus

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    """Service for syncing data with Google Sheets."""

    # Sheet names
    PIPELINES_SHEET = "Pipelines"
    INTERVIEWS_SHEET = "Interviews"
    QUESTIONS_SHEET = "Questions"
    CONTACTS_SHEET = "Contacts"

    # Column headers for each sheet
    PIPELINE_HEADERS = [
        "ID", "Company", "Role", "Job URL", "Stage", "Applied Date",
        "Salary Range", "Location", "Remote Policy", "Priority",
        "Notes", "Created At", "Updated At"
    ]

    INTERVIEW_HEADERS = [
        "ID", "Pipeline ID", "Company", "Role", "Stage", "Round",
        "Scheduled Date", "Duration (min)", "Mode", "Meeting Link",
        "Interviewer Name", "Interviewer Title", "Topics",
        "Prep Status", "Confidence", "Outcome", "Feedback",
        "Self Assessment", "Thank You Sent", "Created At"
    ]

    QUESTION_HEADERS = [
        "ID", "Interview ID", "Question", "Type", "My Answer",
        "Ideal Answer", "Rating", "Gap Identified", "Action Item",
        "Tags", "Created At"
    ]

    CONTACT_HEADERS = [
        "ID", "Pipeline ID", "Company", "Name", "Role",
        "Email", "Phone", "LinkedIn", "Notes", "Created At"
    ]

    def __init__(self, spreadsheet_id: Optional[str] = None):
        self._spreadsheet_id = spreadsheet_id
        self._service = None

    @property
    def is_connected(self) -> bool:
        """Check if connected to Google Sheets."""
        return self._service is not None and self._spreadsheet_id is not None

    def connect(self) -> bool:
        """Connect to Google Sheets API."""
        auth_manager = get_auth_manager()
        credentials = auth_manager.get_credentials()

        if not credentials:
            logger.warning("Not authenticated with Google")
            return False

        try:
            self._service = build('sheets', 'v4', credentials=credentials)
            logger.info("Connected to Google Sheets API")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Sheets API: {e}")
            return False

    def set_spreadsheet_id(self, spreadsheet_id: str):
        """Set the spreadsheet ID to use."""
        self._spreadsheet_id = spreadsheet_id

    def create_spreadsheet(self, title: str = "Interview Tracker") -> Optional[str]:
        """
        Create a new spreadsheet with the required sheets.

        Returns:
            The spreadsheet ID if successful, None otherwise.
        """
        if not self._service:
            if not self.connect():
                return None

        try:
            spreadsheet = {
                'properties': {'title': title},
                'sheets': [
                    {'properties': {'title': self.PIPELINES_SHEET}},
                    {'properties': {'title': self.INTERVIEWS_SHEET}},
                    {'properties': {'title': self.QUESTIONS_SHEET}},
                    {'properties': {'title': self.CONTACTS_SHEET}},
                ]
            }

            result = self._service.spreadsheets().create(
                body=spreadsheet,
                fields='spreadsheetId'
            ).execute()

            self._spreadsheet_id = result.get('spreadsheetId')
            logger.info(f"Created spreadsheet: {self._spreadsheet_id}")

            # Initialize headers
            self._initialize_headers()

            return self._spreadsheet_id

        except HttpError as e:
            logger.error(f"Failed to create spreadsheet: {e}")
            return None

    def _initialize_headers(self):
        """Initialize header rows in all sheets."""
        headers_data = [
            (self.PIPELINES_SHEET, self.PIPELINE_HEADERS),
            (self.INTERVIEWS_SHEET, self.INTERVIEW_HEADERS),
            (self.QUESTIONS_SHEET, self.QUESTION_HEADERS),
            (self.CONTACTS_SHEET, self.CONTACT_HEADERS),
        ]

        for sheet_name, headers in headers_data:
            self._write_row(sheet_name, 1, headers)

    def _write_row(self, sheet_name: str, row: int, values: List[Any]):
        """Write a row to a sheet."""
        range_name = f"{sheet_name}!A{row}"
        body = {'values': [values]}

        try:
            self._service.spreadsheets().values().update(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
        except HttpError as e:
            logger.error(f"Failed to write row: {e}")

    def _append_row(self, sheet_name: str, values: List[Any]):
        """Append a row to a sheet."""
        range_name = f"{sheet_name}!A:A"
        body = {'values': [values]}

        try:
            self._service.spreadsheets().values().append(
                spreadsheetId=self._spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
        except HttpError as e:
            logger.error(f"Failed to append row: {e}")

    def _read_all_rows(self, sheet_name: str) -> List[List[Any]]:
        """Read all rows from a sheet."""
        range_name = f"{sheet_name}!A:Z"

        try:
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except HttpError as e:
            logger.error(f"Failed to read rows: {e}")
            return []

    def _clear_sheet(self, sheet_name: str):
        """Clear all data from a sheet (except headers)."""
        range_name = f"{sheet_name}!A2:Z"

        try:
            self._service.spreadsheets().values().clear(
                spreadsheetId=self._spreadsheet_id,
                range=range_name
            ).execute()
        except HttpError as e:
            logger.error(f"Failed to clear sheet: {e}")

    def _find_row_by_id(self, sheet_name: str, record_id: int) -> Optional[int]:
        """Find the row number for a record by ID."""
        rows = self._read_all_rows(sheet_name)
        for i, row in enumerate(rows[1:], start=2):  # Skip header
            if row and str(row[0]) == str(record_id):
                return i
        return None

    # =========================================================================
    # Pipeline Sync
    # =========================================================================

    def sync_pipeline(self, pipeline: Pipeline) -> bool:
        """Sync a single pipeline to the sheet."""
        if not self.is_connected:
            return False

        row_data = [
            pipeline.id,
            pipeline.company,
            pipeline.role,
            pipeline.job_url or "",
            pipeline.current_stage,
            pipeline.applied_date.isoformat() if pipeline.applied_date else "",
            pipeline.salary_range or "",
            pipeline.location or "",
            pipeline.remote_policy or "",
            pipeline.priority,
            pipeline.notes or "",
            pipeline.created_at.isoformat() if pipeline.created_at else "",
            pipeline.updated_at.isoformat() if pipeline.updated_at else "",
        ]

        existing_row = self._find_row_by_id(self.PIPELINES_SHEET, pipeline.id)

        try:
            if existing_row:
                self._write_row(self.PIPELINES_SHEET, existing_row, row_data)
            else:
                self._append_row(self.PIPELINES_SHEET, row_data)
            return True
        except Exception as e:
            logger.error(f"Failed to sync pipeline: {e}")
            return False

    def sync_all_pipelines(self, pipelines: List[Pipeline]) -> bool:
        """Sync all pipelines to the sheet (full replace)."""
        if not self.is_connected:
            return False

        try:
            self._clear_sheet(self.PIPELINES_SHEET)

            for pipeline in pipelines:
                self.sync_pipeline(pipeline)

            return True
        except Exception as e:
            logger.error(f"Failed to sync all pipelines: {e}")
            return False

    def fetch_pipelines(self) -> List[Dict[str, Any]]:
        """Fetch all pipelines from the sheet."""
        if not self.is_connected:
            return []

        rows = self._read_all_rows(self.PIPELINES_SHEET)
        if len(rows) <= 1:  # Only headers or empty
            return []

        pipelines = []
        headers = self.PIPELINE_HEADERS

        for row in rows[1:]:  # Skip header
            if not row or not row[0]:  # Skip empty rows
                continue

            pipeline_data = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                pipeline_data[header] = value

            pipelines.append(pipeline_data)

        return pipelines

    # =========================================================================
    # Interview Sync
    # =========================================================================

    def sync_interview(self, interview: Interview, pipeline: Pipeline) -> bool:
        """Sync a single interview to the sheet."""
        if not self.is_connected:
            return False

        topics = json.dumps(interview.topics) if interview.topics else ""

        row_data = [
            interview.id,
            interview.pipeline_id,
            pipeline.company,
            pipeline.role,
            interview.stage,
            interview.round_number,
            interview.scheduled_date.isoformat() if interview.scheduled_date else "",
            interview.duration_minutes,
            interview.mode,
            interview.meeting_link or "",
            interview.interviewer_name or "",
            interview.interviewer_title or "",
            topics,
            interview.prep_status,
            interview.confidence or "",
            interview.outcome,
            interview.feedback_received or "",
            interview.self_assessment or "",
            "Yes" if interview.thank_you_sent else "No",
            interview.created_at.isoformat() if interview.created_at else "",
        ]

        existing_row = self._find_row_by_id(self.INTERVIEWS_SHEET, interview.id)

        try:
            if existing_row:
                self._write_row(self.INTERVIEWS_SHEET, existing_row, row_data)
            else:
                self._append_row(self.INTERVIEWS_SHEET, row_data)
            return True
        except Exception as e:
            logger.error(f"Failed to sync interview: {e}")
            return False

    def sync_all_interviews(self, interviews: List[tuple]) -> bool:
        """Sync all interviews to the sheet. Expects list of (interview, pipeline) tuples."""
        if not self.is_connected:
            return False

        try:
            self._clear_sheet(self.INTERVIEWS_SHEET)

            for interview, pipeline in interviews:
                self.sync_interview(interview, pipeline)

            return True
        except Exception as e:
            logger.error(f"Failed to sync all interviews: {e}")
            return False

    def fetch_interviews(self) -> List[Dict[str, Any]]:
        """Fetch all interviews from the sheet."""
        if not self.is_connected:
            return []

        rows = self._read_all_rows(self.INTERVIEWS_SHEET)
        if len(rows) <= 1:
            return []

        interviews = []
        headers = self.INTERVIEW_HEADERS

        for row in rows[1:]:
            if not row or not row[0]:
                continue

            interview_data = {}
            for i, header in enumerate(headers):
                value = row[i] if i < len(row) else ""
                interview_data[header] = value

            interviews.append(interview_data)

        return interviews

    # =========================================================================
    # Question Sync
    # =========================================================================

    def sync_question(self, question: InterviewQuestion, interview: Optional[Interview] = None) -> bool:
        """Sync a single question to the sheet."""
        if not self.is_connected:
            return False

        tags = json.dumps(question.tags) if question.tags else ""

        row_data = [
            question.id,
            question.interview_id or "",
            question.question_text,
            question.question_type,
            question.my_answer or "",
            question.ideal_answer or "",
            question.rating or "",
            question.gap_identified or "",
            question.action_item or "",
            tags,
            question.created_at.isoformat() if question.created_at else "",
        ]

        existing_row = self._find_row_by_id(self.QUESTIONS_SHEET, question.id)

        try:
            if existing_row:
                self._write_row(self.QUESTIONS_SHEET, existing_row, row_data)
            else:
                self._append_row(self.QUESTIONS_SHEET, row_data)
            return True
        except Exception as e:
            logger.error(f"Failed to sync question: {e}")
            return False

    # =========================================================================
    # Full Sync
    # =========================================================================

    def full_sync_to_sheet(self, session) -> bool:
        """
        Perform a full sync from local database to Google Sheets.

        Args:
            session: SQLAlchemy session with loaded data
        """
        if not self.is_connected:
            if not self.connect():
                return False

        from sqlalchemy import select
        from ..core.models import Pipeline, Interview, InterviewQuestion, Contact

        try:
            # Sync pipelines
            pipelines = list(session.execute(select(Pipeline)).scalars().all())
            self.sync_all_pipelines(pipelines)
            logger.info(f"Synced {len(pipelines)} pipelines to sheet")

            # Sync interviews with their pipelines
            interviews = list(session.execute(select(Interview)).scalars().all())
            interview_tuples = []
            for interview in interviews:
                pipeline = session.get(Pipeline, interview.pipeline_id)
                if pipeline:
                    interview_tuples.append((interview, pipeline))
            self.sync_all_interviews(interview_tuples)
            logger.info(f"Synced {len(interviews)} interviews to sheet")

            # Sync questions
            questions = list(session.execute(select(InterviewQuestion)).scalars().all())
            self._clear_sheet(self.QUESTIONS_SHEET)
            for question in questions:
                self.sync_question(question)
            logger.info(f"Synced {len(questions)} questions to sheet")

            return True

        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            return False

    def get_spreadsheet_url(self) -> Optional[str]:
        """Get the URL of the current spreadsheet."""
        if self._spreadsheet_id:
            return f"https://docs.google.com/spreadsheets/d/{self._spreadsheet_id}"
        return None


# Global sheets service instance
_sheets_service: Optional[GoogleSheetsService] = None


def get_sheets_service() -> GoogleSheetsService:
    """Get the global sheets service instance."""
    global _sheets_service
    if _sheets_service is None:
        _sheets_service = GoogleSheetsService()
    return _sheets_service

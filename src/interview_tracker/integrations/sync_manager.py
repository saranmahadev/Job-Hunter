"""Sync manager for online/offline data synchronization."""

import json
import socket
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any
import logging

from ..data.database import get_db, get_data_directory
from ..core.models import Pipeline, Interview, InterviewQuestion
from .google_auth import get_auth_manager
from .google_sheets import get_sheets_service, GoogleSheetsService
from .google_calendar import get_calendar_service, GoogleCalendarService

logger = logging.getLogger(__name__)


class SyncStatus(str, Enum):
    """Current sync status."""
    OFFLINE = "offline"
    ONLINE = "online"
    SYNCING = "syncing"
    ERROR = "error"


class SyncMode(str, Enum):
    """Data synchronization mode."""
    LOCAL_ONLY = "local_only"  # No sync, SQLite only
    SYNC_ON_CHANGE = "sync_on_change"  # Sync to sheets on every change
    SYNC_PERIODIC = "sync_periodic"  # Sync periodically
    SHEETS_PRIMARY = "sheets_primary"  # Google Sheets is primary, sync down


class SyncConfig:
    """Configuration for sync behavior."""

    def __init__(self):
        self.mode: SyncMode = SyncMode.LOCAL_ONLY
        self.spreadsheet_id: Optional[str] = None
        self.calendar_id: str = "primary"
        self.sync_calendar: bool = True
        self.sync_interval_minutes: int = 5
        self.last_sync: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'mode': self.mode.value,
            'spreadsheet_id': self.spreadsheet_id,
            'calendar_id': self.calendar_id,
            'sync_calendar': self.sync_calendar,
            'sync_interval_minutes': self.sync_interval_minutes,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncConfig':
        config = cls()
        config.mode = SyncMode(data.get('mode', 'local_only'))
        config.spreadsheet_id = data.get('spreadsheet_id')
        config.calendar_id = data.get('calendar_id', 'primary')
        config.sync_calendar = data.get('sync_calendar', True)
        config.sync_interval_minutes = data.get('sync_interval_minutes', 5)
        if data.get('last_sync'):
            config.last_sync = datetime.fromisoformat(data['last_sync'])
        return config


class SyncManager:
    """
    Manages synchronization between local SQLite and Google services.

    Behavior:
    - When OFFLINE: All operations use local SQLite
    - When ONLINE with SYNC_ON_CHANGE: Changes are immediately synced to Google Sheets
    - When ONLINE with SHEETS_PRIMARY: Google Sheets is the source of truth
    """

    CONFIG_FILE = "sync_config.json"

    def __init__(self):
        self._status = SyncStatus.OFFLINE
        self._config = SyncConfig()
        self._callbacks: List[Callable[[SyncStatus], None]] = []
        self._sync_thread: Optional[threading.Thread] = None
        self._running = False
        self._sheets_service: Optional[GoogleSheetsService] = None
        self._calendar_service: Optional[GoogleCalendarService] = None

        self._load_config()

    @property
    def status(self) -> SyncStatus:
        return self._status

    @property
    def config(self) -> SyncConfig:
        return self._config

    @property
    def is_online(self) -> bool:
        return self._status in [SyncStatus.ONLINE, SyncStatus.SYNCING]

    def register_status_callback(self, callback: Callable[[SyncStatus], None]):
        """Register a callback to be notified of status changes."""
        self._callbacks.append(callback)

    def _notify_status_change(self, new_status: SyncStatus):
        """Notify all callbacks of a status change."""
        self._status = new_status
        for callback in self._callbacks:
            try:
                callback(new_status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")

    def _load_config(self):
        """Load sync configuration from disk."""
        config_path = get_data_directory() / self.CONFIG_FILE
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                self._config = SyncConfig.from_dict(data)
                logger.info("Loaded sync configuration")
            except Exception as e:
                logger.warning(f"Failed to load sync config: {e}")

    def save_config(self):
        """Save sync configuration to disk."""
        config_path = get_data_directory() / self.CONFIG_FILE
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.info("Saved sync configuration")
        except Exception as e:
            logger.error(f"Failed to save sync config: {e}")

    def check_connectivity(self) -> bool:
        """Check if we have internet connectivity."""
        try:
            socket.create_connection(("www.google.com", 80), timeout=3)
            return True
        except OSError:
            return False

    def initialize(self) -> bool:
        """
        Initialize the sync manager.

        Checks authentication and connectivity, connects to services if possible.
        """
        # Check if we're in local-only mode
        if self._config.mode == SyncMode.LOCAL_ONLY:
            self._notify_status_change(SyncStatus.OFFLINE)
            logger.info("Sync mode is LOCAL_ONLY, staying offline")
            return True

        # Check connectivity
        if not self.check_connectivity():
            self._notify_status_change(SyncStatus.OFFLINE)
            logger.info("No internet connectivity, staying offline")
            return True

        # Check authentication
        auth_manager = get_auth_manager()
        if not auth_manager.is_authenticated:
            self._notify_status_change(SyncStatus.OFFLINE)
            logger.info("Not authenticated with Google, staying offline")
            return True

        # Try to connect to services
        try:
            self._sheets_service = get_sheets_service()
            if self._config.spreadsheet_id:
                self._sheets_service.set_spreadsheet_id(self._config.spreadsheet_id)

            if not self._sheets_service.connect():
                self._notify_status_change(SyncStatus.OFFLINE)
                return True

            if self._config.sync_calendar:
                self._calendar_service = get_calendar_service()
                self._calendar_service.set_calendar_id(self._config.calendar_id)
                self._calendar_service.connect()

            self._notify_status_change(SyncStatus.ONLINE)
            logger.info("Sync manager initialized and online")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize sync: {e}")
            self._notify_status_change(SyncStatus.ERROR)
            return False

    def start_periodic_sync(self):
        """Start background periodic sync thread."""
        if self._running:
            return

        if self._config.mode not in [SyncMode.SYNC_PERIODIC, SyncMode.SHEETS_PRIMARY]:
            return

        self._running = True
        self._sync_thread = threading.Thread(target=self._periodic_sync_loop, daemon=True)
        self._sync_thread.start()
        logger.info("Started periodic sync thread")

    def stop_periodic_sync(self):
        """Stop background periodic sync thread."""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        logger.info("Stopped periodic sync thread")

    def _periodic_sync_loop(self):
        """Background loop for periodic sync."""
        while self._running:
            interval = self._config.sync_interval_minutes * 60

            # Wait for interval in small chunks to allow quick shutdown
            for _ in range(interval):
                if not self._running:
                    return
                time.sleep(1)

            if self._running and self.is_online:
                self.sync_all()

    def sync_all(self) -> bool:
        """Perform a full sync of all data."""
        if not self.is_online:
            logger.warning("Cannot sync while offline")
            return False

        if self._config.mode == SyncMode.LOCAL_ONLY:
            return True

        self._notify_status_change(SyncStatus.SYNCING)

        try:
            db = get_db()

            with db.session_scope() as session:
                if self._sheets_service and self._config.spreadsheet_id:
                    self._sheets_service.full_sync_to_sheet(session)

            self._config.last_sync = datetime.utcnow()
            self.save_config()

            self._notify_status_change(SyncStatus.ONLINE)
            logger.info("Full sync completed successfully")
            return True

        except Exception as e:
            logger.error(f"Full sync failed: {e}")
            self._notify_status_change(SyncStatus.ERROR)
            return False

    def sync_pipeline(self, pipeline: Pipeline) -> bool:
        """Sync a single pipeline to Google Sheets."""
        if not self.is_online or self._config.mode == SyncMode.LOCAL_ONLY:
            return True

        if self._config.mode != SyncMode.SYNC_ON_CHANGE:
            return True

        if not self._sheets_service or not self._config.spreadsheet_id:
            return True

        try:
            return self._sheets_service.sync_pipeline(pipeline)
        except Exception as e:
            logger.error(f"Failed to sync pipeline: {e}")
            return False

    def sync_interview(self, interview: Interview, pipeline: Pipeline) -> bool:
        """Sync a single interview to Google Sheets and Calendar."""
        if not self.is_online or self._config.mode == SyncMode.LOCAL_ONLY:
            return True

        if self._config.mode != SyncMode.SYNC_ON_CHANGE:
            return True

        success = True

        # Sync to sheets
        if self._sheets_service and self._config.spreadsheet_id:
            try:
                success = self._sheets_service.sync_interview(interview, pipeline)
            except Exception as e:
                logger.error(f"Failed to sync interview to sheets: {e}")
                success = False

        # Sync to calendar
        if self._calendar_service and self._config.sync_calendar and interview.scheduled_date:
            try:
                # Check if event already exists
                event_id = self._calendar_service.find_event_by_interview(interview, pipeline)
                if event_id:
                    self._calendar_service.update_interview_event(event_id, interview, pipeline)
                else:
                    self._calendar_service.create_interview_event(interview, pipeline)
            except Exception as e:
                logger.error(f"Failed to sync interview to calendar: {e}")
                # Don't fail the whole sync for calendar issues

        return success

    def create_calendar_event(self, interview: Interview, pipeline: Pipeline) -> Optional[str]:
        """Create a calendar event for an interview."""
        if not self.is_online or not self._calendar_service:
            return None

        if not self._config.sync_calendar:
            return None

        try:
            return self._calendar_service.create_interview_event(interview, pipeline)
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None

    def setup_google_integration(
        self,
        spreadsheet_id: Optional[str] = None,
        create_new_sheet: bool = False,
        sheet_title: str = "Interview Tracker",
    ) -> bool:
        """
        Set up Google integration.

        Args:
            spreadsheet_id: Existing spreadsheet ID to use
            create_new_sheet: Whether to create a new spreadsheet
            sheet_title: Title for new spreadsheet if creating
        """
        auth_manager = get_auth_manager()

        # Check authentication
        if not auth_manager.is_authenticated:
            if not auth_manager.authenticate():
                return False

        # Connect to services
        self._sheets_service = get_sheets_service()
        if not self._sheets_service.connect():
            return False

        # Set up spreadsheet
        if spreadsheet_id:
            self._config.spreadsheet_id = spreadsheet_id
            self._sheets_service.set_spreadsheet_id(spreadsheet_id)
        elif create_new_sheet:
            new_id = self._sheets_service.create_spreadsheet(sheet_title)
            if not new_id:
                return False
            self._config.spreadsheet_id = new_id

        # Set up calendar
        if self._config.sync_calendar:
            self._calendar_service = get_calendar_service()
            self._calendar_service.connect()
            self._calendar_service.set_calendar_id(self._config.calendar_id)

        # Update config
        self._config.mode = SyncMode.SYNC_ON_CHANGE
        self.save_config()

        self._notify_status_change(SyncStatus.ONLINE)
        return True

    def get_spreadsheet_url(self) -> Optional[str]:
        """Get the URL of the connected spreadsheet."""
        if self._sheets_service:
            return self._sheets_service.get_spreadsheet_url()
        return None

    def disconnect(self):
        """Disconnect from Google services and go offline."""
        self._config.mode = SyncMode.LOCAL_ONLY
        self.save_config()
        self.stop_periodic_sync()
        self._notify_status_change(SyncStatus.OFFLINE)
        logger.info("Disconnected from Google services")


# Global sync manager instance
_sync_manager: Optional[SyncManager] = None


def get_sync_manager() -> SyncManager:
    """Get the global sync manager instance."""
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager()
    return _sync_manager

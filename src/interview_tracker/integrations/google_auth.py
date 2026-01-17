"""Google OAuth authentication manager."""

import os
import json
import pickle
from pathlib import Path
from typing import Optional, List
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from ..data.database import get_data_directory

logger = logging.getLogger(__name__)

# Scopes required for Google Sheets and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]


class GoogleAuthManager:
    """Manages Google OAuth2 authentication."""

    def __init__(self):
        self._credentials: Optional[Credentials] = None
        self._data_dir = get_data_directory()
        self._token_path = self._data_dir / 'token.pickle'
        self._credentials_path = self._data_dir / 'credentials.json'

    @property
    def is_authenticated(self) -> bool:
        """Check if we have valid credentials."""
        creds = self.get_credentials()
        return creds is not None and creds.valid

    @property
    def credentials_file_exists(self) -> bool:
        """Check if the credentials.json file exists."""
        return self._credentials_path.exists()

    def save_credentials_file(self, source_path: str) -> bool:
        """
        Save the provided credentials file to the application data directory.
        
        Args:
            source_path: Path to the source credentials.json file.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            import shutil
            shutil.copy2(source_path, self._credentials_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save credentials file: {e}")
            return False

    def get_credentials(self) -> Optional[Credentials]:
        """Get valid credentials, refreshing if necessary."""
        if self._credentials and self._credentials.valid:
            return self._credentials

        # Try to load from saved token
        if self._token_path.exists():
            try:
                with open(self._token_path, 'rb') as token:
                    self._credentials = pickle.load(token)
            except Exception as e:
                logger.warning(f"Failed to load saved credentials: {e}")
                self._credentials = None

        # Check if credentials need refresh
        if self._credentials and self._credentials.expired and self._credentials.refresh_token:
            try:
                self._credentials.refresh(Request())
                self._save_credentials()
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                self._credentials = None

        return self._credentials if self._credentials and self._credentials.valid else None

    def authenticate(self) -> bool:
        """
        Perform OAuth2 authentication flow.

        Requires credentials.json to be present in the data directory.
        Opens a browser for the user to authorize the application.

        Returns:
            True if authentication was successful, False otherwise.
        """
        if not self._credentials_path.exists():
            logger.error(
                f"credentials.json not found at {self._credentials_path}. "
                "Please download it from Google Cloud Console."
            )
            return False

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(self._credentials_path),
                SCOPES
            )
            self._credentials = flow.run_local_server(port=0)
            self._save_credentials()
            logger.info("Successfully authenticated with Google")
            return True
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _save_credentials(self):
        """Save credentials to disk."""
        try:
            with open(self._token_path, 'wb') as token:
                pickle.dump(self._credentials, token)
        except Exception as e:
            logger.warning(f"Failed to save credentials: {e}")

    def revoke(self):
        """Revoke and clear stored credentials."""
        self._credentials = None
        if self._token_path.exists():
            try:
                self._token_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete token file: {e}")

    def get_credentials_setup_instructions(self) -> str:
        """Return instructions for setting up Google API credentials."""
        return """
To enable Google Sheets and Calendar sync, you need to set up Google API credentials:

1. Go to the Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Calendar API
4. Go to "Credentials" and create an "OAuth 2.0 Client ID"
   - Application type: Desktop app
   - Download the credentials JSON file
5. Rename the downloaded file to "credentials.json"
6. Place it in: {data_dir}
7. Click "Authenticate with Google" in the app

Note: Keep your credentials.json file secure and never share it.
""".format(data_dir=self._data_dir)


# Global auth manager instance
_auth_manager: Optional[GoogleAuthManager] = None


def get_auth_manager() -> GoogleAuthManager:
    """Get the global auth manager instance."""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = GoogleAuthManager()
    return _auth_manager

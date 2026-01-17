
import customtkinter as ctk
import webbrowser
from typing import Callable, Optional
from tkinter import filedialog

from ..theme import Colors, Fonts, Spacing, Dimensions
from ..components.data_table import StatusBadge
from ...integrations.sync_manager import get_sync_manager, SyncStatus, SyncMode
from ...integrations.google_auth import get_auth_manager
from ...data.database import get_database_path, get_data_directory


class SettingsView(ctk.CTkFrame):
    """Settings view with sync configuration."""

    def __init__(
        self,
        master,
        on_sync_status_change: Optional[Callable[[SyncStatus], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_sync_status_change = on_sync_status_change
        self._sync_manager = get_sync_manager()
        self._auth_manager = get_auth_manager()

        self._create_widgets()
        self._refresh_status()

        # Register for sync status updates
        self._sync_manager.register_status_callback(self._on_status_update)

    def _create_widgets(self):
        """Create settings widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Settings",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left")

        # Scrollable content
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE)

        # =====================================================================
        # Sync Status Card
        # =====================================================================
        status_card = self._create_card(content, "Sync Status")

        status_inner = ctk.CTkFrame(status_card, fg_color="transparent")
        status_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Current status
        status_row = ctk.CTkFrame(status_inner, fg_color="transparent")
        status_row.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(
            status_row,
            text="Current Status:",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left")

        self._status_badge = ctk.CTkFrame(status_row, fg_color=Colors.TEXT_MUTED, corner_radius=4)
        self._status_badge.pack(side="left", padx=Spacing.PADDING_SMALL)
        self._status_label = ctk.CTkLabel(
            self._status_badge,
            text="Offline",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_PRIMARY,
        )
        self._status_label.pack(padx=Spacing.PADDING_SMALL, pady=2)

        # Last sync time
        self._last_sync_label = ctk.CTkLabel(
            status_inner,
            text="Last sync: Never",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        )
        self._last_sync_label.pack(anchor="w", pady=Spacing.PADDING_SMALL)

        # Sync mode
        mode_row = ctk.CTkFrame(status_inner, fg_color="transparent")
        mode_row.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(
            mode_row,
            text="Sync Mode:",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left")

        self._mode_dropdown = ctk.CTkOptionMenu(
            mode_row,
            values=[
                "Local Only (Offline)",
                "Sync on Change",
                "Sync Periodically",
            ],
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            command=self._on_mode_change,
            width=180,
        )
        self._mode_dropdown.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Manual sync button
        self._sync_btn = ctk.CTkButton(
            status_inner,
            text="Sync Now",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_sync_now,
        )
        self._sync_btn.pack(anchor="w", pady=Spacing.PADDING_NORMAL)

        # =====================================================================
        # Google Account Card
        # =====================================================================
        google_card = self._create_card(content, "Google Account")

        google_inner = ctk.CTkFrame(google_card, fg_color="transparent")
        google_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Auth status
        auth_row = ctk.CTkFrame(google_inner, fg_color="transparent")
        auth_row.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(
            auth_row,
            text="Authentication:",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left")

        self._auth_status_label = ctk.CTkLabel(
            auth_row,
            text="Not authenticated",
            font=Fonts.get("normal"),
            text_color=Colors.DANGER,
        )
        self._auth_status_label.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Auth buttons
        auth_btn_frame = ctk.CTkFrame(google_inner, fg_color="transparent")
        auth_btn_frame.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        self._auth_btn = ctk.CTkButton(
            auth_btn_frame,
            text="Authenticate with Google",
            font=Fonts.get("normal"),
            fg_color=Colors.SUCCESS,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_authenticate,
        )
        self._auth_btn.pack(side="left", padx=(0, Spacing.PADDING_SMALL))

        self._disconnect_btn = ctk.CTkButton(
            auth_btn_frame,
            text="Disconnect",
            font=Fonts.get("normal"),
            fg_color=Colors.DANGER,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_disconnect,
        )
        self._disconnect_btn.pack(side="left")

        # Instructions
        self._instructions_label = ctk.CTkLabel(
            google_inner,
            text="",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
            wraplength=500,
            justify="left",
        )
        self._instructions_label.pack(anchor="w", pady=Spacing.PADDING_SMALL)

        # =====================================================================
        # Google Sheets Card
        # =====================================================================
        sheets_card = self._create_card(content, "Google Sheets")

        sheets_inner = ctk.CTkFrame(sheets_card, fg_color="transparent")
        sheets_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Spreadsheet ID
        ctk.CTkLabel(
            sheets_inner,
            text="Spreadsheet ID:",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w")

        sheet_id_row = ctk.CTkFrame(sheets_inner, fg_color="transparent")
        sheet_id_row.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._sheet_id_entry = ctk.CTkEntry(
            sheet_id_row,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            placeholder_text="Enter existing spreadsheet ID or create new",
            width=350,
        )
        self._sheet_id_entry.pack(side="left", padx=(0, Spacing.PADDING_SMALL))

        save_id_btn = ctk.CTkButton(
            sheet_id_row,
            text="Save",
            font=Fonts.get("normal"),
            fg_color=Colors.SECONDARY,
            height=Dimensions.INPUT_HEIGHT,
            width=60,
            command=self._on_save_sheet_id,
        )
        save_id_btn.pack(side="left")

        # Create new sheet button
        sheet_btn_frame = ctk.CTkFrame(sheets_inner, fg_color="transparent")
        sheet_btn_frame.pack(fill="x", pady=Spacing.PADDING_SMALL)

        create_sheet_btn = ctk.CTkButton(
            sheet_btn_frame,
            text="Create New Spreadsheet",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_create_sheet,
        )
        create_sheet_btn.pack(side="left", padx=(0, Spacing.PADDING_SMALL))

        self._open_sheet_btn = ctk.CTkButton(
            sheet_btn_frame,
            text="Open in Browser",
            font=Fonts.get("normal"),
            fg_color=Colors.INFO,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_open_sheet,
        )
        self._open_sheet_btn.pack(side="left")

        # =====================================================================
        # Google Calendar Card
        # =====================================================================
        calendar_card = self._create_card(content, "Google Calendar")

        calendar_inner = ctk.CTkFrame(calendar_card, fg_color="transparent")
        calendar_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Enable calendar sync
        self._calendar_var = ctk.BooleanVar(value=True)
        calendar_check = ctk.CTkCheckBox(
            calendar_inner,
            text="Sync interviews to Google Calendar",
            variable=self._calendar_var,
            font=Fonts.get("normal"),
            command=self._on_calendar_toggle,
        )
        calendar_check.pack(anchor="w", pady=Spacing.PADDING_SMALL)

        # Calendar selection
        calendar_row = ctk.CTkFrame(calendar_inner, fg_color="transparent")
        calendar_row.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(
            calendar_row,
            text="Calendar:",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(side="left")

        self._calendar_dropdown = ctk.CTkOptionMenu(
            calendar_row,
            values=["Primary Calendar"],
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            width=200,
        )
        self._calendar_dropdown.pack(side="left", padx=Spacing.PADDING_SMALL)

        # =====================================================================
        # Data Storage Card
        # =====================================================================
        storage_card = self._create_card(content, "Data Storage")

        storage_inner = ctk.CTkFrame(storage_card, fg_color="transparent")
        storage_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Database path
        db_path = get_database_path()
        ctk.CTkLabel(
            storage_inner,
            text="Local Database:",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w")

        ctk.CTkLabel(
            storage_inner,
            text=str(db_path),
            font=Fonts.get("small"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w", pady=(0, Spacing.PADDING_NORMAL))

        # Config directory
        config_dir = get_data_directory()
        ctk.CTkLabel(
            storage_inner,
            text="Configuration Directory:",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w")

        ctk.CTkLabel(
            storage_inner,
            text=str(config_dir),
            font=Fonts.get("small"),
            text_color=Colors.TEXT_SECONDARY,
        ).pack(anchor="w")

        # Info text
        info_text = (
            "\nWhen online, data is synced to Google Sheets as the primary backend. "
            "When offline, all changes are saved locally and will sync when back online."
        )
        ctk.CTkLabel(
            storage_inner,
            text=info_text,
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=Spacing.PADDING_NORMAL)

    def _create_card(self, parent, title: str) -> ctk.CTkFrame:
        """Create a settings card with title."""
        card = ctk.CTkFrame(
            parent,
            fg_color=Colors.BG_CARD,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
        )
        card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        header = ctk.CTkLabel(
            card,
            text=title,
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, 0))

        return card

    def _refresh_status(self):
        """Refresh the display based on current status."""
        # Update sync status
        status = self._sync_manager.status
        status_colors = {
            SyncStatus.OFFLINE: Colors.TEXT_MUTED,
            SyncStatus.ONLINE: Colors.SUCCESS,
            SyncStatus.SYNCING: Colors.INFO,
            SyncStatus.ERROR: Colors.DANGER,
        }
        self._status_badge.configure(fg_color=status_colors.get(status, Colors.TEXT_MUTED))
        self._status_label.configure(text=status.value.capitalize())

        # Update last sync time
        config = self._sync_manager.config
        if config.last_sync:
            self._last_sync_label.configure(
                text=f"Last sync: {config.last_sync.strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            self._last_sync_label.configure(text="Last sync: Never")

        # Update mode dropdown
        mode_map = {
            SyncMode.LOCAL_ONLY: "Local Only (Offline)",
            SyncMode.SYNC_ON_CHANGE: "Sync on Change",
            SyncMode.SYNC_PERIODIC: "Sync Periodically",
        }
        self._mode_dropdown.set(mode_map.get(config.mode, "Local Only (Offline)"))

        # Update auth status
        if self._auth_manager.is_authenticated:
            self._auth_status_label.configure(text="Authenticated", text_color=Colors.SUCCESS)
            self._auth_btn.configure(state="disabled")
            self._disconnect_btn.configure(state="normal")
            self._instructions_label.configure(text="")
        else:
            self._auth_status_label.configure(text="Not authenticated", text_color=Colors.DANGER)
            self._auth_btn.configure(state="normal")
            self._disconnect_btn.configure(state="disabled")

            if not self._auth_manager.credentials_file_exists:
                self._instructions_label.configure(
                    text=self._auth_manager.get_credentials_setup_instructions()
                )
                
                # Add upload button if it doesn't exist
                if not hasattr(self, "_upload_btn"):
                    self._upload_btn = ctk.CTkButton(
                        self._instructions_label.master,
                        text="Upload credentials.json",
                        font=Fonts.get("normal"),
                        fg_color=Colors.SECONDARY,
                        height=Dimensions.BUTTON_HEIGHT,
                        command=self._on_upload_credentials,
                    )
                    self._upload_btn.pack(anchor="w", pady=Spacing.PADDING_SMALL)
            else:
                 # if credentials exist, remove the upload button if present
                 if hasattr(self, "_upload_btn"):
                     self._upload_btn.destroy()
                     delattr(self, "_upload_btn")

        # Update sheet ID
        if config.spreadsheet_id:
            self._sheet_id_entry.delete(0, "end")
            self._sheet_id_entry.insert(0, config.spreadsheet_id)
            self._open_sheet_btn.configure(state="normal")
        else:
            self._open_sheet_btn.configure(state="disabled")

        # Update calendar settings
        self._calendar_var.set(config.sync_calendar)

        # Enable/disable sync button
        if self._sync_manager.is_online:
            self._sync_btn.configure(state="normal")
        else:
            self._sync_btn.configure(state="disabled")

    def _on_status_update(self, status: SyncStatus):
        """Handle sync status update."""
        self._refresh_status()
        if self._on_sync_status_change:
            self._on_sync_status_change(status)

    def _on_mode_change(self, value: str):
        """Handle sync mode change."""
        mode_map = {
            "Local Only (Offline)": SyncMode.LOCAL_ONLY,
            "Sync on Change": SyncMode.SYNC_ON_CHANGE,
            "Sync Periodically": SyncMode.SYNC_PERIODIC,
        }
        new_mode = mode_map.get(value, SyncMode.LOCAL_ONLY)
        self._sync_manager.config.mode = new_mode
        self._sync_manager.save_config()

        # Re-initialize sync manager
        self._sync_manager.initialize()
        self._refresh_status()

    def _on_sync_now(self):
        """Handle manual sync."""
        self._sync_btn.configure(state="disabled", text="Syncing...")
        self.update_idletasks()

        success = self._sync_manager.sync_all()

        self._sync_btn.configure(state="normal", text="Sync Now")
        self._refresh_status()

    def _on_authenticate(self):
        """Handle Google authentication."""
        self._auth_btn.configure(state="disabled", text="Authenticating...")
        self.update_idletasks()

        success = self._auth_manager.authenticate()

        if success:
            # Initialize sync manager
            self._sync_manager.initialize()

        self._auth_btn.configure(text="Authenticate with Google")
        self._refresh_status()

    def _on_disconnect(self):
        """Handle disconnect from Google."""
        self._auth_manager.revoke()
        self._sync_manager.disconnect()
        self._refresh_status()

    def _on_save_sheet_id(self):
        """Handle saving spreadsheet ID."""
        sheet_id = self._sheet_id_entry.get().strip()
        if sheet_id:
            self._sync_manager.config.spreadsheet_id = sheet_id
            self._sync_manager.save_config()
            self._refresh_status()

    def _on_create_sheet(self):
        """Handle creating a new spreadsheet."""
        if not self._auth_manager.is_authenticated:
            return

        success = self._sync_manager.setup_google_integration(create_new_sheet=True)
        self._refresh_status()

        if success:
            # Open the new spreadsheet
            self._on_open_sheet()

    def _on_open_sheet(self):
        """Open the spreadsheet in browser."""
        url = self._sync_manager.get_spreadsheet_url()
        if url:
            webbrowser.open(url)

    def _on_calendar_toggle(self):
        """Handle calendar sync toggle."""
        self._sync_manager.config.sync_calendar = self._calendar_var.get()
        self._sync_manager.save_config()

    def _on_upload_credentials(self):
        """Handle uploading credentials.json file."""
        filename = filedialog.askopenfilename(
            title="Select credentials.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            if self._auth_manager.save_credentials_file(filename):
                self._refresh_status()
                # Optionally show success message (though status update might be enough)
            else:
                # Show error (could be improved with a message dialog)
                pass

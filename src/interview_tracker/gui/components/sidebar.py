"""Sidebar navigation component."""

import customtkinter as ctk
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions


class SidebarButton(ctk.CTkButton):
    """A button for the sidebar navigation."""

    def __init__(
        self,
        master,
        text: str,
        icon: str = "",
        command: Optional[Callable] = None,
        **kwargs
    ):
        super().__init__(
            master,
            text=f"  {icon}  {text}" if icon else text,
            command=command,
            anchor="w",
            height=40,
            corner_radius=8,
            font=Fonts.get("normal"),
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.SIDEBAR_HOVER,
            **kwargs
        )
        self._is_active = False

    def set_active(self, active: bool):
        """Set the active state of the button."""
        self._is_active = active
        if active:
            self.configure(
                fg_color=Colors.SIDEBAR_ACTIVE,
                text_color=Colors.TEXT_PRIMARY,
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=Colors.TEXT_SECONDARY,
            )


class Sidebar(ctk.CTkFrame):
    """Sidebar navigation component."""

    def __init__(self, master, on_navigate: Callable[[str], None], **kwargs):
        super().__init__(
            master,
            width=Dimensions.SIDEBAR_WIDTH,
            corner_radius=0,
            fg_color=Colors.SIDEBAR_BG,
            **kwargs
        )
        self.on_navigate = on_navigate
        self._buttons: dict[str, SidebarButton] = {}
        self._current_view = "dashboard"

        self._create_widgets()

    def _create_widgets(self):
        """Create sidebar widgets."""
        # Logo / Title
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=Spacing.PADDING_NORMAL, pady=Spacing.PADDING_LARGE)

        title_label = ctk.CTkLabel(
            title_frame,
            text="Interview",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="Tracker",
            font=Fonts.get("medium"),
            text_color=Colors.PRIMARY,
        )
        subtitle_label.pack(anchor="w")

        # Separator
        separator = ctk.CTkFrame(self, height=1, fg_color=Colors.BG_LIGHT)
        separator.pack(fill="x", padx=Spacing.PADDING_NORMAL, pady=Spacing.PADDING_NORMAL)

        # Navigation buttons
        nav_items = [
            ("dashboard", "Dashboard", "\U0001F4CA"),  # Chart emoji
            ("pipelines", "Pipelines", "\U0001F4CB"),  # Clipboard emoji
            ("interviews", "Interviews", "\U0001F4C5"),  # Calendar emoji
            ("questions", "Questions", "\u2753"),  # Question mark emoji
        ]

        for view_id, label, icon in nav_items:
            btn = SidebarButton(
                self,
                text=label,
                icon=icon,
                command=lambda v=view_id: self._on_button_click(v),
            )
            btn.pack(fill="x", padx=Spacing.PADDING_SMALL, pady=2)
            self._buttons[view_id] = btn

        # Set initial active state
        self._buttons["dashboard"].set_active(True)

        # Spacer
        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        # Bottom section
        bottom_separator = ctk.CTkFrame(self, height=1, fg_color=Colors.BG_LIGHT)
        bottom_separator.pack(fill="x", padx=Spacing.PADDING_NORMAL, pady=Spacing.PADDING_NORMAL)

        # Settings button
        settings_btn = SidebarButton(
            self,
            text="Settings",
            icon="\u2699",  # Gear emoji
            command=lambda: self._on_button_click("settings"),
        )
        settings_btn.pack(fill="x", padx=Spacing.PADDING_SMALL, pady=2)
        self._buttons["settings"] = settings_btn

        # Version info
        version_label = ctk.CTkLabel(
            self,
            text="v1.0.0",
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        )
        version_label.pack(pady=Spacing.PADDING_NORMAL)

    def _on_button_click(self, view_id: str):
        """Handle navigation button click."""
        if view_id == self._current_view:
            return

        # Update button states
        for vid, btn in self._buttons.items():
            btn.set_active(vid == view_id)

        self._current_view = view_id
        self.on_navigate(view_id)

    def set_active_view(self, view_id: str):
        """Programmatically set the active view."""
        if view_id in self._buttons:
            self._on_button_click(view_id)

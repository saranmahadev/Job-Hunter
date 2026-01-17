"""Data table component for displaying lists of items."""

import customtkinter as ctk
from typing import List, Dict, Any, Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions


class DataTable(ctk.CTkScrollableFrame):
    """A scrollable table for displaying data."""

    def __init__(
        self,
        master,
        columns: List[Dict[str, Any]],
        on_row_click: Optional[Callable[[int, Dict], None]] = None,
        on_row_double_click: Optional[Callable[[int, Dict], None]] = None,
        **kwargs
    ):
        """
        Initialize the data table.

        Args:
            columns: List of column definitions with keys:
                - key: Data key for this column
                - title: Display title
                - width: Column width (optional)
                - align: Text alignment ('left', 'center', 'right')
                - render: Custom render function (optional)
            on_row_click: Callback for single click
            on_row_double_click: Callback for double click
        """
        super().__init__(
            master,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            fg_color=Colors.BG_CARD,
            **kwargs
        )

        self._columns = columns
        self._on_row_click = on_row_click
        self._on_row_double_click = on_row_double_click
        self._data: List[Dict] = []
        self._row_frames: List[ctk.CTkFrame] = []
        self._selected_row: Optional[int] = None

        self._create_header()

    def _create_header(self):
        """Create the table header."""
        header_frame = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_MEDIUM,
            corner_radius=0,
        )
        header_frame.pack(fill="x", pady=(0, 1))

        for col in self._columns:
            width = col.get("width", 150)
            align = col.get("align", "left")

            label = ctk.CTkLabel(
                header_frame,
                text=col["title"],
                font=Fonts.get("normal", "bold"),
                text_color=Colors.TEXT_SECONDARY,
                width=width,
                anchor=self._get_anchor(align),
            )
            label.pack(side="left", padx=Spacing.PADDING_SMALL, pady=Spacing.PADDING_SMALL)

    def _get_anchor(self, align: str) -> str:
        """Convert alignment to anchor."""
        return {"left": "w", "center": "center", "right": "e"}.get(align, "w")

    def set_data(self, data: List[Dict]):
        """Set the table data."""
        # Clear existing rows
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames.clear()
        self._data = data
        self._selected_row = None

        # Create new rows
        for idx, row_data in enumerate(data):
            self._create_row(idx, row_data)

    def _create_row(self, index: int, row_data: Dict):
        """Create a single data row."""
        bg_color = Colors.BG_CARD if index % 2 == 0 else Colors.BG_LIGHT

        row_frame = ctk.CTkFrame(
            self,
            fg_color=bg_color,
            corner_radius=0,
        )
        row_frame.pack(fill="x", pady=(0, 1))

        # Bind click events
        row_frame.bind("<Button-1>", lambda e, i=index: self._on_click(i))
        row_frame.bind("<Double-Button-1>", lambda e, i=index: self._on_double_click(i))

        for col in self._columns:
            width = col.get("width", 150)
            align = col.get("align", "left")
            key = col["key"]

            # Get the value
            value = row_data.get(key, "")

            # Apply custom render if provided
            if "render" in col:
                widget = col["render"](row_frame, value, row_data)
                if widget:
                    widget.pack(side="left", padx=Spacing.PADDING_SMALL, pady=Spacing.PADDING_SMALL)
                    widget.bind("<Button-1>", lambda e, i=index: self._on_click(i))
                    widget.bind("<Double-Button-1>", lambda e, i=index: self._on_double_click(i))
            else:
                label = ctk.CTkLabel(
                    row_frame,
                    text=str(value),
                    font=Fonts.get("normal"),
                    text_color=Colors.TEXT_PRIMARY,
                    width=width,
                    anchor=self._get_anchor(align),
                )
                label.pack(side="left", padx=Spacing.PADDING_SMALL, pady=Spacing.PADDING_SMALL)
                label.bind("<Button-1>", lambda e, i=index: self._on_click(i))
                label.bind("<Double-Button-1>", lambda e, i=index: self._on_double_click(i))

        self._row_frames.append(row_frame)

    def _on_click(self, index: int):
        """Handle row click."""
        # Update selection highlighting
        if self._selected_row is not None and self._selected_row < len(self._row_frames):
            old_bg = Colors.BG_CARD if self._selected_row % 2 == 0 else Colors.BG_LIGHT
            self._row_frames[self._selected_row].configure(fg_color=old_bg)

        self._selected_row = index
        self._row_frames[index].configure(fg_color=Colors.PRIMARY_HOVER)

        if self._on_row_click and index < len(self._data):
            self._on_row_click(index, self._data[index])

    def _on_double_click(self, index: int):
        """Handle row double click."""
        if self._on_row_double_click and index < len(self._data):
            self._on_row_double_click(index, self._data[index])

    def get_selected(self) -> Optional[Dict]:
        """Get the currently selected row data."""
        if self._selected_row is not None and self._selected_row < len(self._data):
            return self._data[self._selected_row]
        return None

    def refresh(self):
        """Refresh the table with current data."""
        self.set_data(self._data)


class StatusBadge(ctk.CTkFrame):
    """A colored badge for displaying status."""

    def __init__(
        self,
        master,
        text: str,
        color: str = Colors.PRIMARY,
        **kwargs
    ):
        super().__init__(
            master,
            corner_radius=4,
            fg_color=color,
            **kwargs
        )

        label = ctk.CTkLabel(
            self,
            text=text,
            font=Fonts.get("small"),
            text_color=Colors.TEXT_PRIMARY,
        )
        label.pack(padx=Spacing.PADDING_SMALL, pady=2)


def create_status_badge_renderer(status_colors: Dict[str, str]):
    """Create a renderer function for status badges."""
    def render(parent, value, row_data):
        color = status_colors.get(value, Colors.TEXT_MUTED)
        return StatusBadge(parent, text=str(value).replace("_", " ").title(), color=color)
    return render

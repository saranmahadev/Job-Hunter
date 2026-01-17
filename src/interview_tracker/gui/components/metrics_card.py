"""Metrics card component for dashboard display."""

import customtkinter as ctk
from typing import Optional

from ..theme import Colors, Fonts, Spacing, Dimensions


class MetricsCard(ctk.CTkFrame):
    """A card displaying a single metric."""

    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: Optional[str] = None,
        color: str = Colors.PRIMARY,
        **kwargs
    ):
        super().__init__(
            master,
            corner_radius=Dimensions.CARD_CORNER_RADIUS,
            fg_color=Colors.BG_CARD,
            **kwargs
        )

        self._title = title
        self._value = value
        self._subtitle = subtitle
        self._color = color

        self._create_widgets()

    def _create_widgets(self):
        """Create card widgets."""
        # Color indicator bar on the left
        indicator = ctk.CTkFrame(
            self,
            width=4,
            corner_radius=2,
            fg_color=self._color,
        )
        indicator.pack(side="left", fill="y", padx=(Spacing.PADDING_SMALL, 0), pady=Spacing.PADDING_SMALL)

        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.PADDING_NORMAL, pady=Spacing.PADDING_NORMAL)

        # Title
        self._title_label = ctk.CTkLabel(
            content,
            text=self._title,
            font=Fonts.get("small"),
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        )
        self._title_label.pack(fill="x")

        # Value
        self._value_label = ctk.CTkLabel(
            content,
            text=self._value,
            font=Fonts.get("xlarge", "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self._value_label.pack(fill="x", pady=(Spacing.PADDING_SMALL, 0))

        # Subtitle (optional)
        if self._subtitle:
            self._subtitle_label = ctk.CTkLabel(
                content,
                text=self._subtitle,
                font=Fonts.get("small"),
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            )
            self._subtitle_label.pack(fill="x")

    def update_value(self, value: str, subtitle: Optional[str] = None):
        """Update the displayed value."""
        self._value_label.configure(text=value)
        if subtitle and hasattr(self, '_subtitle_label'):
            self._subtitle_label.configure(text=subtitle)


class MetricsRow(ctk.CTkFrame):
    """A row of metrics cards."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._cards: dict[str, MetricsCard] = {}

    def add_card(
        self,
        key: str,
        title: str,
        value: str,
        subtitle: Optional[str] = None,
        color: str = Colors.PRIMARY,
    ) -> MetricsCard:
        """Add a metrics card to the row."""
        card = MetricsCard(
            self,
            title=title,
            value=value,
            subtitle=subtitle,
            color=color,
        )
        card.pack(side="left", fill="both", expand=True, padx=Spacing.PADDING_SMALL)
        self._cards[key] = card
        return card

    def update_card(self, key: str, value: str, subtitle: Optional[str] = None):
        """Update a specific card's value."""
        if key in self._cards:
            self._cards[key].update_value(value, subtitle)

    def get_card(self, key: str) -> Optional[MetricsCard]:
        """Get a card by key."""
        return self._cards.get(key)

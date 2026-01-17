"""Theme and styling configuration for the GUI."""

import customtkinter as ctk


# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Colors:
    """Color palette for the application."""

    # Primary colors
    PRIMARY = "#1f6aa5"
    PRIMARY_HOVER = "#144870"
    SECONDARY = "#2b2b2b"

    # Background colors
    BG_DARK = "#1a1a1a"
    BG_MEDIUM = "#242424"
    BG_LIGHT = "#2b2b2b"
    BG_CARD = "#333333"

    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#b0b0b0"
    TEXT_MUTED = "#808080"

    # Status colors
    SUCCESS = "#28a745"
    SUCCESS_LIGHT = "#34d058"
    WARNING = "#ffc107"
    WARNING_LIGHT = "#ffda6a"
    DANGER = "#dc3545"
    DANGER_LIGHT = "#f97583"
    INFO = "#17a2b8"
    INFO_LIGHT = "#3fc3dc"

    # Pipeline health colors
    HEALTH_ACTIVE = "#28a745"
    HEALTH_AWAITING = "#ffc107"
    HEALTH_FOLLOWUP = "#fd7e14"
    HEALTH_STALE = "#dc3545"
    HEALTH_CLOSED = "#6c757d"

    # Prep status colors
    PREP_NOT_STARTED = "#dc3545"
    PREP_IN_PROGRESS = "#ffc107"
    PREP_READY = "#28a745"

    # Priority colors
    PRIORITY_LOW = "#6c757d"
    PRIORITY_MEDIUM = "#17a2b8"
    PRIORITY_HIGH = "#ffc107"
    PRIORITY_VERY_HIGH = "#fd7e14"
    PRIORITY_CRITICAL = "#dc3545"

    # Sidebar
    SIDEBAR_BG = "#1f1f1f"
    SIDEBAR_HOVER = "#2d2d2d"
    SIDEBAR_ACTIVE = "#1f6aa5"


class Fonts:
    """Font configurations."""

    # Font families
    FAMILY = "Segoe UI"
    FAMILY_MONO = "Consolas"

    # Sizes
    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_MEDIUM = 15
    SIZE_LARGE = 18
    SIZE_XLARGE = 24
    SIZE_TITLE = 32

    @classmethod
    def get(cls, size: str = "normal", weight: str = "normal") -> tuple:
        """Get a font tuple for CustomTkinter."""
        sizes = {
            "small": cls.SIZE_SMALL,
            "normal": cls.SIZE_NORMAL,
            "medium": cls.SIZE_MEDIUM,
            "large": cls.SIZE_LARGE,
            "xlarge": cls.SIZE_XLARGE,
            "title": cls.SIZE_TITLE,
        }
        return (cls.FAMILY, sizes.get(size, cls.SIZE_NORMAL), weight)


class Spacing:
    """Spacing constants."""

    PADDING_SMALL = 5
    PADDING_NORMAL = 10
    PADDING_MEDIUM = 15
    PADDING_LARGE = 20
    PADDING_XLARGE = 30

    MARGIN_SMALL = 5
    MARGIN_NORMAL = 10
    MARGIN_MEDIUM = 15
    MARGIN_LARGE = 20


class Dimensions:
    """Size constants."""

    # Window
    WINDOW_MIN_WIDTH = 1200
    WINDOW_MIN_HEIGHT = 700
    WINDOW_DEFAULT_WIDTH = 1400
    WINDOW_DEFAULT_HEIGHT = 850

    # Sidebar
    SIDEBAR_WIDTH = 200
    SIDEBAR_COLLAPSED_WIDTH = 60

    # Cards
    CARD_WIDTH = 280
    CARD_HEIGHT = 120
    CARD_CORNER_RADIUS = 10

    # Buttons
    BUTTON_HEIGHT = 36
    BUTTON_CORNER_RADIUS = 8

    # Input fields
    INPUT_HEIGHT = 36
    INPUT_CORNER_RADIUS = 6

    # Tables
    TABLE_ROW_HEIGHT = 40
    TABLE_HEADER_HEIGHT = 45


def get_health_color(health_value: str) -> str:
    """Get the color for a pipeline health status."""
    colors = {
        "active": Colors.HEALTH_ACTIVE,
        "awaiting": Colors.HEALTH_AWAITING,
        "needs_followup": Colors.HEALTH_FOLLOWUP,
        "stale": Colors.HEALTH_STALE,
        "closed": Colors.HEALTH_CLOSED,
    }
    return colors.get(health_value, Colors.TEXT_MUTED)


def get_prep_color(prep_status: str) -> str:
    """Get the color for a preparation status."""
    colors = {
        "not_started": Colors.PREP_NOT_STARTED,
        "in_progress": Colors.PREP_IN_PROGRESS,
        "ready": Colors.PREP_READY,
    }
    return colors.get(prep_status, Colors.TEXT_MUTED)


def get_priority_color(priority: int) -> str:
    """Get the color for a priority level."""
    colors = {
        1: Colors.PRIORITY_LOW,
        2: Colors.PRIORITY_MEDIUM,
        3: Colors.PRIORITY_HIGH,
        4: Colors.PRIORITY_VERY_HIGH,
        5: Colors.PRIORITY_CRITICAL,
    }
    return colors.get(priority, Colors.TEXT_MUTED)


def get_outcome_color(outcome: str) -> str:
    """Get the color for an interview outcome."""
    colors = {
        "pending": Colors.WARNING,
        "passed": Colors.SUCCESS,
        "failed": Colors.DANGER,
        "rescheduled": Colors.INFO,
    }
    return colors.get(outcome, Colors.TEXT_MUTED)

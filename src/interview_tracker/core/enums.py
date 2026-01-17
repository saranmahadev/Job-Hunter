"""Enumerations for Interview Tracker."""

from enum import Enum


class PipelineStage(str, Enum):
    """Pipeline stages representing the interview process."""
    APPLIED = "applied"
    RECRUITER_SCREEN = "recruiter_screen"
    TECH_ROUND_1 = "tech_round_1"
    TECH_ROUND_2 = "tech_round_2"
    SYSTEM_DESIGN = "system_design"
    AI_ROUND = "ai_round"
    HM_ROUND = "hm_round"
    FINAL_CULTURE = "final_culture"
    OFFER = "offer"
    REJECTED = "rejected"
    DROPPED = "dropped"

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        names = {
            "applied": "Applied",
            "recruiter_screen": "Recruiter Screen",
            "tech_round_1": "Technical Round 1",
            "tech_round_2": "Technical Round 2",
            "system_design": "System Design",
            "ai_round": "AI / GenAI Round",
            "hm_round": "Hiring Manager",
            "final_culture": "Final / Culture",
            "offer": "Offer",
            "rejected": "Rejected",
            "dropped": "Dropped",
        }
        return names.get(self.value, self.value)

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in {PipelineStage.OFFER, PipelineStage.REJECTED, PipelineStage.DROPPED}


class InterviewMode(str, Enum):
    """Interview delivery mode."""
    VIDEO = "video"
    PHONE = "phone"
    ONSITE = "onsite"
    TAKE_HOME = "take_home"

    @property
    def display_name(self) -> str:
        names = {
            "video": "Video Call",
            "phone": "Phone",
            "onsite": "On-site",
            "take_home": "Take-home",
        }
        return names.get(self.value, self.value)


class InterviewOutcome(str, Enum):
    """Interview outcome status."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    RESCHEDULED = "rescheduled"

    @property
    def display_name(self) -> str:
        return self.value.capitalize()


class PrepStatus(str, Enum):
    """Preparation status for an interview."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY = "ready"

    @property
    def display_name(self) -> str:
        names = {
            "not_started": "Not Started",
            "in_progress": "In Progress",
            "ready": "Ready",
        }
        return names.get(self.value, self.value)

    @property
    def color(self) -> str:
        """Color for UI display."""
        colors = {
            "not_started": "#dc3545",  # Red
            "in_progress": "#ffc107",  # Yellow
            "ready": "#28a745",  # Green
        }
        return colors.get(self.value, "#6c757d")


class PipelineHealth(str, Enum):
    """Calculated health status of a pipeline."""
    ACTIVE = "active"
    AWAITING = "awaiting"
    NEEDS_FOLLOWUP = "needs_followup"
    STALE = "stale"
    CLOSED = "closed"

    @property
    def display_name(self) -> str:
        names = {
            "active": "Active",
            "awaiting": "Awaiting Response",
            "needs_followup": "Needs Follow-up",
            "stale": "Stale",
            "closed": "Closed",
        }
        return names.get(self.value, self.value)

    @property
    def color(self) -> str:
        """Color for UI display."""
        colors = {
            "active": "#28a745",  # Green
            "awaiting": "#ffc107",  # Yellow
            "needs_followup": "#fd7e14",  # Orange
            "stale": "#dc3545",  # Red
            "closed": "#6c757d",  # Gray
        }
        return colors.get(self.value, "#6c757d")

    @property
    def emoji(self) -> str:
        """Emoji indicator for the health status."""
        emojis = {
            "active": "🟢",
            "awaiting": "🟡",
            "needs_followup": "🟠",
            "stale": "🔴",
            "closed": "⚫",
        }
        return emojis.get(self.value, "⚪")


class QuestionType(str, Enum):
    """Type of interview question."""
    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SYSTEM_DESIGN = "system_design"
    CODING = "coding"
    CULTURE = "culture"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        names = {
            "behavioral": "Behavioral",
            "technical": "Technical",
            "system_design": "System Design",
            "coding": "Coding",
            "culture": "Culture Fit",
            "other": "Other",
        }
        return names.get(self.value, self.value)


class PrepCategory(str, Enum):
    """Category for preparation topics."""
    DATA_STRUCTURES = "data_structures"
    ALGORITHMS = "algorithms"
    SYSTEM_DESIGN = "system_design"
    BEHAVIORAL = "behavioral"
    DOMAIN_SPECIFIC = "domain_specific"
    AI_ML = "ai_ml"
    OTHER = "other"

    @property
    def display_name(self) -> str:
        names = {
            "data_structures": "Data Structures",
            "algorithms": "Algorithms",
            "system_design": "System Design",
            "behavioral": "Behavioral",
            "domain_specific": "Domain Specific",
            "ai_ml": "AI / Machine Learning",
            "other": "Other",
        }
        return names.get(self.value, self.value)


class Priority(int, Enum):
    """Priority level for pipelines."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4
    CRITICAL = 5

    @property
    def display_name(self) -> str:
        names = {
            1: "Low",
            2: "Medium",
            3: "High",
            4: "Very High",
            5: "Critical",
        }
        return names.get(self.value, str(self.value))

    @property
    def color(self) -> str:
        colors = {
            1: "#6c757d",  # Gray
            2: "#17a2b8",  # Cyan
            3: "#ffc107",  # Yellow
            4: "#fd7e14",  # Orange
            5: "#dc3545",  # Red
        }
        return colors.get(self.value, "#6c757d")

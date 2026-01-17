"""Pipeline state machine for managing valid transitions."""

from typing import Set, Dict, Optional

from .enums import PipelineStage


class PipelineStateMachine:
    """Manages valid state transitions for interview pipelines."""

    # Define valid transitions: current_state -> set of valid next states
    TRANSITIONS: Dict[PipelineStage, Set[PipelineStage]] = {
        PipelineStage.APPLIED: {
            PipelineStage.RECRUITER_SCREEN,
            PipelineStage.TECH_ROUND_1,  # Some skip recruiter
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.RECRUITER_SCREEN: {
            PipelineStage.TECH_ROUND_1,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.TECH_ROUND_1: {
            PipelineStage.TECH_ROUND_2,
            PipelineStage.SYSTEM_DESIGN,
            PipelineStage.AI_ROUND,
            PipelineStage.HM_ROUND,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.TECH_ROUND_2: {
            PipelineStage.SYSTEM_DESIGN,
            PipelineStage.AI_ROUND,
            PipelineStage.HM_ROUND,
            PipelineStage.FINAL_CULTURE,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.SYSTEM_DESIGN: {
            PipelineStage.AI_ROUND,
            PipelineStage.HM_ROUND,
            PipelineStage.FINAL_CULTURE,
            PipelineStage.OFFER,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.AI_ROUND: {
            PipelineStage.HM_ROUND,
            PipelineStage.FINAL_CULTURE,
            PipelineStage.OFFER,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.HM_ROUND: {
            PipelineStage.FINAL_CULTURE,
            PipelineStage.OFFER,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.FINAL_CULTURE: {
            PipelineStage.OFFER,
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
        },
        PipelineStage.OFFER: {
            PipelineStage.DROPPED,  # Can decline offer
        },
        PipelineStage.REJECTED: set(),  # Terminal state
        PipelineStage.DROPPED: set(),  # Terminal state
    }

    # Define stage order for progression tracking
    STAGE_ORDER: Dict[PipelineStage, int] = {
        PipelineStage.APPLIED: 0,
        PipelineStage.RECRUITER_SCREEN: 1,
        PipelineStage.TECH_ROUND_1: 2,
        PipelineStage.TECH_ROUND_2: 3,
        PipelineStage.SYSTEM_DESIGN: 4,
        PipelineStage.AI_ROUND: 4,  # Same level as system design
        PipelineStage.HM_ROUND: 5,
        PipelineStage.FINAL_CULTURE: 6,
        PipelineStage.OFFER: 7,
        PipelineStage.REJECTED: -1,  # Terminal
        PipelineStage.DROPPED: -1,  # Terminal
    }

    @classmethod
    def can_transition(cls, from_stage: PipelineStage, to_stage: PipelineStage) -> bool:
        """Check if a transition from one stage to another is valid."""
        return to_stage in cls.TRANSITIONS.get(from_stage, set())

    @classmethod
    def get_valid_transitions(cls, current_stage: PipelineStage) -> Set[PipelineStage]:
        """Get all valid next stages from the current stage."""
        return cls.TRANSITIONS.get(current_stage, set())

    @classmethod
    def is_terminal(cls, stage: PipelineStage) -> bool:
        """Check if a stage is terminal (no further transitions possible)."""
        return stage in {
            PipelineStage.REJECTED,
            PipelineStage.DROPPED,
            PipelineStage.OFFER,
        }

    @classmethod
    def is_positive_terminal(cls, stage: PipelineStage) -> bool:
        """Check if the stage is a positive outcome."""
        return stage == PipelineStage.OFFER

    @classmethod
    def is_negative_terminal(cls, stage: PipelineStage) -> bool:
        """Check if the stage is a negative outcome."""
        return stage in {PipelineStage.REJECTED, PipelineStage.DROPPED}

    @classmethod
    def get_stage_order(cls, stage: PipelineStage) -> int:
        """Get the ordinal position of a stage (for sorting/progress)."""
        return cls.STAGE_ORDER.get(stage, 0)

    @classmethod
    def is_progressing(cls, from_stage: PipelineStage, to_stage: PipelineStage) -> bool:
        """Check if the transition represents forward progress."""
        if cls.is_negative_terminal(to_stage):
            return False
        from_order = cls.get_stage_order(from_stage)
        to_order = cls.get_stage_order(to_stage)
        return to_order > from_order

    @classmethod
    def get_progress_percentage(cls, stage: PipelineStage) -> int:
        """Get the progress percentage for a stage (0-100)."""
        if cls.is_negative_terminal(stage):
            return 0
        if stage == PipelineStage.OFFER:
            return 100

        order = cls.get_stage_order(stage)
        max_order = cls.get_stage_order(PipelineStage.OFFER)

        if max_order == 0:
            return 0
        return int((order / max_order) * 100)

    @classmethod
    def get_next_logical_stages(cls, current_stage: PipelineStage) -> Set[PipelineStage]:
        """
        Get the most likely next stages (excluding terminal states).
        Useful for UI suggestions.
        """
        valid = cls.get_valid_transitions(current_stage)
        return {s for s in valid if not cls.is_negative_terminal(s)}

    @classmethod
    def validate_transition(
        cls, from_stage: PipelineStage, to_stage: PipelineStage
    ) -> tuple[bool, Optional[str]]:
        """
        Validate a transition and return a tuple of (is_valid, error_message).
        """
        if from_stage == to_stage:
            return False, "Cannot transition to the same stage"

        if cls.is_terminal(from_stage) and from_stage != PipelineStage.OFFER:
            return False, f"Cannot transition from terminal stage: {from_stage.display_name}"

        if not cls.can_transition(from_stage, to_stage):
            valid_stages = [s.display_name for s in cls.get_valid_transitions(from_stage)]
            return False, (
                f"Invalid transition from {from_stage.display_name} to {to_stage.display_name}. "
                f"Valid options: {', '.join(valid_stages)}"
            )

        return True, None


class TransitionError(Exception):
    """Exception raised when an invalid pipeline transition is attempted."""

    def __init__(self, from_stage: PipelineStage, to_stage: PipelineStage, message: str):
        self.from_stage = from_stage
        self.to_stage = to_stage
        self.message = message
        super().__init__(message)

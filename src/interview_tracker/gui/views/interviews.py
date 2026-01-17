"""Interview list and detail views."""

import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions, get_prep_color, get_outcome_color
from ..components.data_table import DataTable, StatusBadge
from ...services.interview import InterviewService
from ...core.enums import PipelineStage, InterviewOutcome, PrepStatus, InterviewMode
from ...data.database import get_db


class InterviewListView(ctk.CTkFrame):
    """View for listing all interviews."""

    def __init__(
        self,
        master,
        on_view_interview: Optional[Callable[[int], None]] = None,
        on_schedule_interview: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_view_interview = on_view_interview
        self._on_schedule_interview = on_schedule_interview
        self._filter_mode = "upcoming"  # "upcoming", "pending", "all"

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create list view widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Interviews",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left")

        # Schedule button
        schedule_btn = ctk.CTkButton(
            header_frame,
            text="+ Schedule Interview",
            font=Fonts.get("normal"),
            fg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_LIGHT,
            height=Dimensions.BUTTON_HEIGHT,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_schedule_click,
        )
        schedule_btn.pack(side="right")

        # Filter tabs
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_NORMAL))

        self._filter_buttons = {}
        filters = [
            ("upcoming", "Upcoming"),
            ("pending", "Pending Results"),
            ("all", "All Interviews"),
        ]

        for filter_id, label in filters:
            btn = ctk.CTkButton(
                filter_frame,
                text=label,
                font=Fonts.get("normal"),
                fg_color=Colors.PRIMARY if filter_id == self._filter_mode else "transparent",
                text_color=Colors.TEXT_PRIMARY if filter_id == self._filter_mode else Colors.TEXT_SECONDARY,
                hover_color=Colors.PRIMARY_HOVER,
                height=32,
                corner_radius=6,
                command=lambda f=filter_id: self._on_filter_change(f),
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[filter_id] = btn

        # Table
        self._table = DataTable(
            self,
            columns=[
                {"key": "company", "title": "Company", "width": 140},
                {"key": "role", "title": "Role", "width": 150},
                {"key": "stage", "title": "Stage", "width": 120},
                {"key": "date", "title": "Date", "width": 120},
                {"key": "mode", "title": "Mode", "width": 80},
                {"key": "prep_status", "title": "Prep", "width": 90,
                 "render": self._render_prep_status},
                {"key": "outcome", "title": "Outcome", "width": 90,
                 "render": self._render_outcome},
            ],
            on_row_double_click=self._on_row_double_click,
        )
        self._table.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_LARGE))

    def _render_prep_status(self, parent, value, row_data):
        """Render prep status as colored badge."""
        color = get_prep_color(value)
        text = value.replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _render_outcome(self, parent, value, row_data):
        """Render outcome as colored badge."""
        color = get_outcome_color(value)
        text = value.replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _on_schedule_click(self):
        if self._on_schedule_interview:
            self._on_schedule_interview()

    def _on_filter_change(self, filter_id: str):
        """Handle filter change."""
        self._filter_mode = filter_id

        # Update button styles
        for fid, btn in self._filter_buttons.items():
            if fid == filter_id:
                btn.configure(fg_color=Colors.PRIMARY, text_color=Colors.TEXT_PRIMARY)
            else:
                btn.configure(fg_color="transparent", text_color=Colors.TEXT_SECONDARY)

        self.refresh()

    def _on_row_double_click(self, index: int, row_data: dict):
        if self._on_view_interview and "id" in row_data:
            self._on_view_interview(row_data["id"])

    def refresh(self):
        """Refresh interview list."""
        db = get_db()

        with db.session_scope() as session:
            interview_service = InterviewService(session)

            if self._filter_mode == "upcoming":
                interviews = interview_service.get_all_upcoming()
            elif self._filter_mode == "pending":
                interviews = interview_service.get_pending_outcomes()
            else:
                # Get all - using upcoming + pending + completed
                from sqlalchemy import select
                from ...core.models import Interview
                stmt = select(Interview).order_by(Interview.scheduled_date.desc()).limit(100)
                interviews = list(session.execute(stmt).scalars().all())

            table_data = []
            for interview in interviews:
                pipeline = interview.pipeline
                stage = PipelineStage(interview.stage)
                mode = InterviewMode(interview.mode)

                date_str = interview.scheduled_date.strftime("%b %d, %H:%M") if interview.scheduled_date else "-"

                table_data.append({
                    "id": interview.id,
                    "company": pipeline.company if pipeline else "-",
                    "role": (pipeline.role[:20] + "...") if pipeline and len(pipeline.role) > 20 else (pipeline.role if pipeline else "-"),
                    "stage": stage.display_name,
                    "date": date_str,
                    "mode": mode.display_name,
                    "prep_status": interview.prep_status,
                    "outcome": interview.outcome,
                })

            self._table.set_data(table_data)


class InterviewDetailView(ctk.CTkFrame):
    """View for displaying interview details."""

    def __init__(
        self,
        master,
        interview_id: int,
        on_back: Optional[Callable[[], None]] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._interview_id = interview_id
        self._on_back = on_back
        self._on_edit = on_edit

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create detail view widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        back_btn = ctk.CTkButton(
            header_frame,
            text="< Back",
            font=Fonts.get("normal"),
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_LIGHT,
            width=80,
            command=self._on_back_click,
        )
        back_btn.pack(side="left")

        self._title_label = ctk.CTkLabel(
            header_frame,
            text="Interview Details",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        self._title_label.pack(side="left", padx=Spacing.PADDING_LARGE)

        # Actions
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_frame.pack(side="right")

        edit_btn = ctk.CTkButton(
            actions_frame,
            text="Edit",
            font=Fonts.get("normal"),
            fg_color=Colors.SECONDARY,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_edit_click,
        )
        edit_btn.pack(side="left", padx=Spacing.PADDING_SMALL)

        self._complete_btn = ctk.CTkButton(
            actions_frame,
            text="Mark Complete",
            font=Fonts.get("normal"),
            fg_color=Colors.SUCCESS,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_complete_click,
        )
        self._complete_btn.pack(side="left")

        # Content
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE)

        # Info card
        info_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        info_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        self._info_labels = {}
        info_fields = [
            ("company", "Company"),
            ("role", "Role"),
            ("stage", "Stage"),
            ("date", "Date & Time"),
            ("mode", "Mode"),
            ("duration", "Duration"),
            ("interviewer", "Interviewer"),
            ("meeting_link", "Meeting Link"),
        ]

        for i, (key, label) in enumerate(info_fields):
            row = i // 2
            col = i % 2

            field_frame = ctk.CTkFrame(info_inner, fg_color="transparent")
            field_frame.grid(row=row, column=col, sticky="w", padx=Spacing.PADDING_NORMAL, pady=Spacing.PADDING_SMALL)

            label_widget = ctk.CTkLabel(
                field_frame,
                text=label,
                font=Fonts.get("small"),
                text_color=Colors.TEXT_MUTED,
            )
            label_widget.pack(anchor="w")

            value_widget = ctk.CTkLabel(
                field_frame,
                text="-",
                font=Fonts.get("normal"),
                text_color=Colors.TEXT_PRIMARY,
            )
            value_widget.pack(anchor="w")
            self._info_labels[key] = value_widget

        info_inner.grid_columnconfigure(0, weight=1)
        info_inner.grid_columnconfigure(1, weight=1)

        # Preparation card
        prep_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        prep_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        prep_header = ctk.CTkLabel(
            prep_card,
            text="Preparation",
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        prep_header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, Spacing.PADDING_SMALL))

        prep_inner = ctk.CTkFrame(prep_card, fg_color="transparent")
        prep_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Prep status
        status_frame = ctk.CTkFrame(prep_inner, fg_color="transparent")
        status_frame.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(status_frame, text="Status:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self._prep_status_badge = ctk.CTkFrame(status_frame, fg_color=Colors.TEXT_MUTED, corner_radius=4)
        self._prep_status_badge.pack(side="left", padx=Spacing.PADDING_SMALL)
        self._prep_status_label = ctk.CTkLabel(self._prep_status_badge, text="-", font=Fonts.get("small"))
        self._prep_status_label.pack(padx=Spacing.PADDING_SMALL, pady=2)

        # Confidence
        confidence_frame = ctk.CTkFrame(prep_inner, fg_color="transparent")
        confidence_frame.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(confidence_frame, text="Confidence:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self._confidence_label = ctk.CTkLabel(confidence_frame, text="-", font=Fonts.get("normal"), text_color=Colors.TEXT_PRIMARY)
        self._confidence_label.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Topics
        topics_label = ctk.CTkLabel(prep_inner, text="Topics to prepare:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY)
        topics_label.pack(anchor="w", pady=(Spacing.PADDING_SMALL, 0))
        self._topics_label = ctk.CTkLabel(prep_inner, text="-", font=Fonts.get("normal"), text_color=Colors.TEXT_PRIMARY, wraplength=500, justify="left")
        self._topics_label.pack(anchor="w")

        # Outcome card
        outcome_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        outcome_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        outcome_header = ctk.CTkLabel(
            outcome_card,
            text="Outcome",
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        outcome_header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, Spacing.PADDING_SMALL))

        outcome_inner = ctk.CTkFrame(outcome_card, fg_color="transparent")
        outcome_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Outcome badge
        outcome_status_frame = ctk.CTkFrame(outcome_inner, fg_color="transparent")
        outcome_status_frame.pack(fill="x", pady=Spacing.PADDING_SMALL)

        ctk.CTkLabel(outcome_status_frame, text="Result:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self._outcome_badge = ctk.CTkFrame(outcome_status_frame, fg_color=Colors.TEXT_MUTED, corner_radius=4)
        self._outcome_badge.pack(side="left", padx=Spacing.PADDING_SMALL)
        self._outcome_label = ctk.CTkLabel(self._outcome_badge, text="-", font=Fonts.get("small"))
        self._outcome_label.pack(padx=Spacing.PADDING_SMALL, pady=2)

        # Feedback
        feedback_label = ctk.CTkLabel(outcome_inner, text="Feedback received:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY)
        feedback_label.pack(anchor="w", pady=(Spacing.PADDING_SMALL, 0))
        self._feedback_label = ctk.CTkLabel(outcome_inner, text="-", font=Fonts.get("normal"), text_color=Colors.TEXT_PRIMARY, wraplength=500, justify="left")
        self._feedback_label.pack(anchor="w")

        # Self assessment
        assess_label = ctk.CTkLabel(outcome_inner, text="Self assessment:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY)
        assess_label.pack(anchor="w", pady=(Spacing.PADDING_SMALL, 0))
        self._assessment_label = ctk.CTkLabel(outcome_inner, text="-", font=Fonts.get("normal"), text_color=Colors.TEXT_PRIMARY, wraplength=500, justify="left")
        self._assessment_label.pack(anchor="w")

    def _on_back_click(self):
        if self._on_back:
            self._on_back()

    def _on_edit_click(self):
        if self._on_edit:
            self._on_edit(self._interview_id)

    def _on_complete_click(self):
        """Handle mark complete button."""
        # This would open a dialog to record outcome
        pass

    def refresh(self):
        """Refresh interview details."""
        db = get_db()

        with db.session_scope() as session:
            interview_service = InterviewService(session)
            interview = interview_service.get_with_pipeline(self._interview_id)

            if not interview:
                return

            pipeline = interview.pipeline
            stage = PipelineStage(interview.stage)
            mode = InterviewMode(interview.mode)
            outcome = InterviewOutcome(interview.outcome)
            prep_status = PrepStatus(interview.prep_status)

            # Update title
            company = pipeline.company if pipeline else "Unknown"
            self._title_label.configure(text=f"{company} - {stage.display_name}")

            # Update info
            self._info_labels["company"].configure(text=company)
            self._info_labels["role"].configure(text=pipeline.role if pipeline else "-")
            self._info_labels["stage"].configure(text=stage.display_name)
            self._info_labels["date"].configure(
                text=interview.scheduled_date.strftime("%B %d, %Y at %H:%M") if interview.scheduled_date else "-"
            )
            self._info_labels["mode"].configure(text=mode.display_name)
            self._info_labels["duration"].configure(text=f"{interview.duration_minutes} minutes")
            self._info_labels["interviewer"].configure(
                text=f"{interview.interviewer_name or '-'}" +
                     (f" ({interview.interviewer_title})" if interview.interviewer_title else "")
            )
            self._info_labels["meeting_link"].configure(
                text=interview.meeting_link[:50] + "..." if interview.meeting_link and len(interview.meeting_link) > 50
                else (interview.meeting_link or "-")
            )

            # Update prep status
            prep_color = get_prep_color(interview.prep_status)
            self._prep_status_badge.configure(fg_color=prep_color)
            self._prep_status_label.configure(text=prep_status.display_name)

            # Update confidence
            if interview.confidence:
                stars = "\u2605" * interview.confidence + "\u2606" * (5 - interview.confidence)
                self._confidence_label.configure(text=f"{stars} ({interview.confidence}/5)")
            else:
                self._confidence_label.configure(text="Not rated")

            # Update topics
            topics = interview.topics
            self._topics_label.configure(text=", ".join(topics) if topics else "No topics specified")

            # Update outcome
            outcome_color = get_outcome_color(interview.outcome)
            self._outcome_badge.configure(fg_color=outcome_color)
            self._outcome_label.configure(text=outcome.display_name)

            self._feedback_label.configure(text=interview.feedback_received or "No feedback yet")
            self._assessment_label.configure(text=interview.self_assessment or "No self-assessment")

            # Update complete button state
            if outcome != InterviewOutcome.PENDING:
                self._complete_btn.configure(state="disabled", text="Completed")
            else:
                self._complete_btn.configure(state="normal", text="Mark Complete")

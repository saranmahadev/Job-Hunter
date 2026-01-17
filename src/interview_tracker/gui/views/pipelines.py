"""Pipeline list and detail views."""

import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional, List

from ..theme import Colors, Fonts, Spacing, Dimensions, get_health_color, get_priority_color
from ..components.data_table import DataTable, StatusBadge
from ...services.pipeline import PipelineService
from ...core.enums import PipelineStage, PipelineHealth, Priority
from ...core.state_machine import PipelineStateMachine
from ...data.database import get_db


class PipelineListView(ctk.CTkFrame):
    """View for listing all pipelines."""

    def __init__(
        self,
        master,
        on_view_pipeline: Optional[Callable[[int], None]] = None,
        on_add_pipeline: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_view_pipeline = on_view_pipeline
        self._on_add_pipeline = on_add_pipeline
        self._include_closed = False

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create list view widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Pipelines",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left")

        # Actions
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_frame.pack(side="right")

        # Show closed toggle
        self._show_closed_var = ctk.BooleanVar(value=False)
        show_closed_check = ctk.CTkCheckBox(
            actions_frame,
            text="Show Closed",
            variable=self._show_closed_var,
            command=self._on_toggle_closed,
            font=Fonts.get("normal"),
        )
        show_closed_check.pack(side="left", padx=Spacing.PADDING_NORMAL)

        # Add button
        add_btn = ctk.CTkButton(
            actions_frame,
            text="+ Add Pipeline",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=Dimensions.BUTTON_HEIGHT,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_add_click,
        )
        add_btn.pack(side="left")

        # Search
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_NORMAL))

        self._search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search by company or role...",
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            width=300,
        )
        self._search_entry.pack(side="left")
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            font=Fonts.get("normal"),
            fg_color=Colors.SECONDARY,
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            width=80,
            command=self._on_search,
        )
        search_btn.pack(side="left", padx=Spacing.PADDING_SMALL)

        clear_btn = ctk.CTkButton(
            search_frame,
            text="Clear",
            font=Fonts.get("normal"),
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_LIGHT,
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            width=60,
            command=self._on_clear_search,
        )
        clear_btn.pack(side="left")

        # Table
        self._table = DataTable(
            self,
            columns=[
                {"key": "company", "title": "Company", "width": 150},
                {"key": "role", "title": "Role", "width": 200},
                {"key": "stage", "title": "Stage", "width": 130,
                 "render": self._render_stage},
                {"key": "health", "title": "Health", "width": 100,
                 "render": self._render_health},
                {"key": "priority", "title": "Priority", "width": 80,
                 "render": self._render_priority},
                {"key": "days_active", "title": "Days", "width": 60, "align": "center"},
                {"key": "updated", "title": "Updated", "width": 100},
            ],
            on_row_double_click=self._on_row_double_click,
        )
        self._table.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_LARGE))

    def _render_stage(self, parent, value, row_data):
        """Render stage as a badge."""
        try:
            stage = PipelineStage(value)
            color = Colors.SUCCESS if stage == PipelineStage.OFFER else (
                Colors.DANGER if stage in [PipelineStage.REJECTED, PipelineStage.DROPPED] else Colors.INFO
            )
            return StatusBadge(parent, text=stage.display_name, color=color)
        except:
            return StatusBadge(parent, text=str(value), color=Colors.TEXT_MUTED)

    def _render_health(self, parent, value, row_data):
        """Render health status as a colored badge."""
        color = get_health_color(value)
        try:
            health = PipelineHealth(value)
            text = health.display_name
        except:
            text = str(value).replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _render_priority(self, parent, value, row_data):
        """Render priority as a colored badge."""
        color = get_priority_color(value)
        try:
            priority = Priority(value)
            text = priority.display_name
        except:
            text = str(value)
        return StatusBadge(parent, text=text, color=color)

    def _on_add_click(self):
        """Handle add button click."""
        if self._on_add_pipeline:
            self._on_add_pipeline()

    def _on_toggle_closed(self):
        """Handle show closed toggle."""
        self._include_closed = self._show_closed_var.get()
        self.refresh()

    def _on_search(self):
        """Handle search."""
        query = self._search_entry.get().strip()
        self.refresh(search_query=query)

    def _on_clear_search(self):
        """Clear search and refresh."""
        self._search_entry.delete(0, "end")
        self.refresh()

    def _on_row_double_click(self, index: int, row_data: dict):
        """Handle row double click."""
        if self._on_view_pipeline and "id" in row_data:
            self._on_view_pipeline(row_data["id"])

    def refresh(self, search_query: Optional[str] = None):
        """Refresh the pipeline list."""
        db = get_db()

        with db.session_scope() as session:
            pipeline_service = PipelineService(session)

            if search_query:
                pipelines = pipeline_service.search(search_query)
            else:
                pipelines = pipeline_service.get_all(include_closed=self._include_closed)

            table_data = []
            for p in pipelines:
                health = pipeline_service.calculate_health(p)
                table_data.append({
                    "id": p.id,
                    "company": p.company,
                    "role": p.role[:30] + "..." if len(p.role) > 30 else p.role,
                    "stage": p.current_stage,
                    "health": health.value,
                    "priority": p.priority,
                    "days_active": p.days_since_applied,
                    "updated": p.updated_at.strftime("%b %d"),
                })

            self._table.set_data(table_data)


class PipelineDetailView(ctk.CTkFrame):
    """View for displaying pipeline details."""

    def __init__(
        self,
        master,
        pipeline_id: int,
        on_back: Optional[Callable[[], None]] = None,
        on_schedule_interview: Optional[Callable[[int], None]] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._pipeline_id = pipeline_id
        self._on_back = on_back
        self._on_schedule_interview = on_schedule_interview
        self._on_edit = on_edit

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create detail view widgets."""
        # Header with back button
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
            text="Pipeline Details",
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

        schedule_btn = ctk.CTkButton(
            actions_frame,
            text="+ Schedule Interview",
            font=Fonts.get("normal"),
            fg_color=Colors.SUCCESS,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_schedule_click,
        )
        schedule_btn.pack(side="left")

        # Content
        content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE)

        # Info card
        info_card = ctk.CTkFrame(content_frame, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        info_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Info grid
        self._info_labels = {}
        info_fields = [
            ("company", "Company"),
            ("role", "Role"),
            ("stage", "Stage"),
            ("health", "Health"),
            ("applied_date", "Applied"),
            ("location", "Location"),
            ("salary", "Salary Range"),
            ("remote", "Remote Policy"),
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

        # Stage progression
        stage_card = ctk.CTkFrame(content_frame, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        stage_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        stage_header = ctk.CTkLabel(
            stage_card,
            text="Stage Progression",
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        stage_header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, Spacing.PADDING_SMALL))

        self._stage_frame = ctk.CTkFrame(stage_card, fg_color="transparent")
        self._stage_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        self._advance_btn = ctk.CTkButton(
            stage_card,
            text="Advance Stage",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_advance_stage,
        )
        self._advance_btn.pack(pady=Spacing.PADDING_NORMAL)

        # Interviews section
        interviews_card = ctk.CTkFrame(content_frame, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        interviews_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        interviews_header = ctk.CTkLabel(
            interviews_card,
            text="Interviews",
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        interviews_header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, Spacing.PADDING_SMALL))

        self._interviews_frame = ctk.CTkFrame(interviews_card, fg_color="transparent")
        self._interviews_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        # Notes section
        notes_card = ctk.CTkFrame(content_frame, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        notes_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        notes_header = ctk.CTkLabel(
            notes_card,
            text="Notes",
            font=Fonts.get("medium", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        notes_header.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=(Spacing.PADDING_NORMAL, Spacing.PADDING_SMALL))

        self._notes_label = ctk.CTkLabel(
            notes_card,
            text="No notes",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_SECONDARY,
            wraplength=600,
            justify="left",
        )
        self._notes_label.pack(anchor="w", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

    def _on_back_click(self):
        if self._on_back:
            self._on_back()

    def _on_edit_click(self):
        if self._on_edit:
            self._on_edit(self._pipeline_id)

    def _on_schedule_click(self):
        if self._on_schedule_interview:
            self._on_schedule_interview(self._pipeline_id)

    def _on_advance_stage(self):
        """Handle advance stage button."""
        # This would open a dialog to select next stage
        pass

    def refresh(self):
        """Refresh pipeline details."""
        db = get_db()

        with db.session_scope() as session:
            pipeline_service = PipelineService(session)
            pipeline = pipeline_service.get_with_interviews(self._pipeline_id)

            if not pipeline:
                return

            # Update title
            self._title_label.configure(text=f"{pipeline.company} - {pipeline.role}")

            # Update info labels
            stage = PipelineStage(pipeline.current_stage)
            health = pipeline_service.calculate_health(pipeline)

            self._info_labels["company"].configure(text=pipeline.company)
            self._info_labels["role"].configure(text=pipeline.role)
            self._info_labels["stage"].configure(text=stage.display_name)
            self._info_labels["health"].configure(text=health.display_name)
            self._info_labels["applied_date"].configure(text=pipeline.applied_date.strftime("%B %d, %Y"))
            self._info_labels["location"].configure(text=pipeline.location or "-")
            self._info_labels["salary"].configure(text=pipeline.salary_range or "-")
            self._info_labels["remote"].configure(text=pipeline.remote_policy or "-")

            # Update notes
            self._notes_label.configure(text=pipeline.notes or "No notes")

            # Update stage progression
            for widget in self._stage_frame.winfo_children():
                widget.destroy()

            stages = [
                PipelineStage.APPLIED,
                PipelineStage.RECRUITER_SCREEN,
                PipelineStage.TECH_ROUND_1,
                PipelineStage.TECH_ROUND_2,
                PipelineStage.SYSTEM_DESIGN,
                PipelineStage.HM_ROUND,
                PipelineStage.FINAL_CULTURE,
                PipelineStage.OFFER,
            ]

            current_order = PipelineStateMachine.get_stage_order(stage)

            for s in stages:
                order = PipelineStateMachine.get_stage_order(s)
                if s == stage:
                    color = Colors.PRIMARY
                elif order < current_order:
                    color = Colors.SUCCESS
                else:
                    color = Colors.BG_LIGHT

                badge = ctk.CTkFrame(
                    self._stage_frame,
                    fg_color=color,
                    corner_radius=4,
                    height=24,
                )
                badge.pack(side="left", padx=2)

                label = ctk.CTkLabel(
                    badge,
                    text=s.display_name[:8],
                    font=Fonts.get("small"),
                    text_color=Colors.TEXT_PRIMARY if color != Colors.BG_LIGHT else Colors.TEXT_MUTED,
                )
                label.pack(padx=Spacing.PADDING_SMALL, pady=2)

            # Update interviews list
            for widget in self._interviews_frame.winfo_children():
                widget.destroy()

            if pipeline.interviews:
                for interview in sorted(pipeline.interviews, key=lambda x: x.scheduled_date or datetime.min, reverse=True):
                    interview_row = ctk.CTkFrame(self._interviews_frame, fg_color=Colors.BG_MEDIUM, corner_radius=6)
                    interview_row.pack(fill="x", pady=2)

                    stage_label = ctk.CTkLabel(
                        interview_row,
                        text=PipelineStage(interview.stage).display_name,
                        font=Fonts.get("normal"),
                        text_color=Colors.TEXT_PRIMARY,
                        width=120,
                    )
                    stage_label.pack(side="left", padx=Spacing.PADDING_SMALL, pady=Spacing.PADDING_SMALL)

                    date_text = interview.scheduled_date.strftime("%b %d, %H:%M") if interview.scheduled_date else "Not scheduled"
                    date_label = ctk.CTkLabel(
                        interview_row,
                        text=date_text,
                        font=Fonts.get("normal"),
                        text_color=Colors.TEXT_SECONDARY,
                    )
                    date_label.pack(side="left", padx=Spacing.PADDING_SMALL)

                    from ..theme import get_outcome_color
                    outcome_badge = StatusBadge(
                        interview_row,
                        text=interview.outcome.replace("_", " ").title(),
                        color=get_outcome_color(interview.outcome),
                    )
                    outcome_badge.pack(side="right", padx=Spacing.PADDING_SMALL, pady=Spacing.PADDING_SMALL)
            else:
                no_interviews = ctk.CTkLabel(
                    self._interviews_frame,
                    text="No interviews scheduled yet",
                    font=Fonts.get("normal"),
                    text_color=Colors.TEXT_MUTED,
                )
                no_interviews.pack(pady=Spacing.PADDING_NORMAL)

            # Update advance button state
            if stage.is_terminal:
                self._advance_btn.configure(state="disabled")
            else:
                self._advance_btn.configure(state="normal")

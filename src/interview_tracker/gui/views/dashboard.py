"""Dashboard view showing overview metrics and upcoming interviews."""

import customtkinter as ctk
from datetime import datetime
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions, get_health_color, get_prep_color
from ..components.metrics_card import MetricsRow
from ..components.data_table import DataTable, StatusBadge
from ...services.metrics import MetricsService
from ...services.pipeline import PipelineService
from ...services.interview import InterviewService
from ...core.enums import PipelineStage, PrepStatus, PipelineHealth
from ...data.database import get_db


class DashboardView(ctk.CTkFrame):
    """Main dashboard view."""

    def __init__(
        self,
        master,
        on_view_pipeline: Optional[Callable[[int], None]] = None,
        on_view_interview: Optional[Callable[[int], None]] = None,
        on_add_pipeline: Optional[Callable[[], None]] = None,
        on_schedule_interview: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_view_pipeline = on_view_pipeline
        self._on_view_interview = on_view_interview
        self._on_add_pipeline = on_add_pipeline
        self._on_schedule_interview = on_schedule_interview

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create dashboard widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Dashboard",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left")

        # Quick action buttons
        actions_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_frame.pack(side="right")

        add_pipeline_btn = ctk.CTkButton(
            actions_frame,
            text="+ Add Pipeline",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=Dimensions.BUTTON_HEIGHT,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_add_pipeline_click,
        )
        add_pipeline_btn.pack(side="left", padx=Spacing.PADDING_SMALL)

        schedule_btn = ctk.CTkButton(
            actions_frame,
            text="+ Schedule Interview",
            font=Fonts.get("normal"),
            fg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_LIGHT,
            height=Dimensions.BUTTON_HEIGHT,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_schedule_click,
        )
        schedule_btn.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Metrics row
        self._metrics_row = MetricsRow(self)
        self._metrics_row.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_LARGE))

        self._metrics_row.add_card(
            "active",
            "Active Pipelines",
            "0",
            color=Colors.SUCCESS
        )
        self._metrics_row.add_card(
            "pass_rate",
            "Pass Rate",
            "0%",
            color=Colors.INFO
        )
        self._metrics_row.add_card(
            "follow_ups",
            "Needs Follow-up",
            "0",
            color=Colors.WARNING
        )
        self._metrics_row.add_card(
            "offers",
            "Offers",
            "0",
            color=Colors.PRIMARY
        )

        # Content area with two columns
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE)
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_columnconfigure(1, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)

        # Left column - Upcoming Interviews
        left_column = ctk.CTkFrame(content_frame, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, Spacing.PADDING_SMALL))

        interviews_header = ctk.CTkLabel(
            left_column,
            text="Upcoming Interviews",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        interviews_header.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._interviews_table = DataTable(
            left_column,
            columns=[
                {"key": "company", "title": "Company", "width": 120},
                {"key": "stage", "title": "Stage", "width": 100},
                {"key": "date", "title": "Date", "width": 100},
                {"key": "prep_status", "title": "Prep", "width": 80,
                 "render": self._render_prep_status},
            ],
            on_row_double_click=self._on_interview_double_click,
        )
        self._interviews_table.pack(fill="both", expand=True)

        # Right column - Pipelines Needing Attention
        right_column = ctk.CTkFrame(content_frame, fg_color="transparent")
        right_column.grid(row=0, column=1, sticky="nsew", padx=(Spacing.PADDING_SMALL, 0))

        attention_header = ctk.CTkLabel(
            right_column,
            text="Needs Attention",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        attention_header.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._attention_table = DataTable(
            right_column,
            columns=[
                {"key": "company", "title": "Company", "width": 120},
                {"key": "role", "title": "Role", "width": 120},
                {"key": "health", "title": "Status", "width": 100,
                 "render": self._render_health_status},
                {"key": "reason", "title": "Reason", "width": 150},
            ],
            on_row_double_click=self._on_pipeline_double_click,
        )
        self._attention_table.pack(fill="both", expand=True)

    def _render_prep_status(self, parent, value, row_data):
        """Render preparation status as a colored badge."""
        color = get_prep_color(value)
        text = value.replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _render_health_status(self, parent, value, row_data):
        """Render health status as a colored badge."""
        color = get_health_color(value)
        text = value.replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _on_add_pipeline_click(self):
        """Handle add pipeline button click."""
        if self._on_add_pipeline:
            self._on_add_pipeline()

    def _on_schedule_click(self):
        """Handle schedule interview button click."""
        if self._on_schedule_interview:
            self._on_schedule_interview()

    def _on_interview_double_click(self, index: int, row_data: dict):
        """Handle interview row double click."""
        if self._on_view_interview and "id" in row_data:
            self._on_view_interview(row_data["id"])

    def _on_pipeline_double_click(self, index: int, row_data: dict):
        """Handle pipeline row double click."""
        if self._on_view_pipeline and "id" in row_data:
            self._on_view_pipeline(row_data["id"])

    def refresh(self):
        """Refresh dashboard data."""
        db = get_db()

        with db.session_scope() as session:
            metrics_service = MetricsService(session)
            pipeline_service = PipelineService(session)
            interview_service = InterviewService(session)

            # Update metrics
            metrics = metrics_service.get_dashboard_metrics()
            self._metrics_row.update_card("active", str(metrics.total_active_pipelines))
            self._metrics_row.update_card("pass_rate", f"{metrics.pass_rate}%")
            self._metrics_row.update_card("follow_ups", str(metrics.pending_follow_ups))
            self._metrics_row.update_card("offers", str(metrics.offers_received))

            # Update upcoming interviews
            upcoming = metrics_service.get_upcoming_interviews(limit=10)
            interviews_data = []
            for interview in upcoming:
                stage_enum = PipelineStage(interview.stage)
                interviews_data.append({
                    "id": interview.id,
                    "company": interview.company,
                    "stage": stage_enum.display_name,
                    "date": interview.scheduled_date.strftime("%b %d, %H:%M"),
                    "prep_status": interview.prep_status,
                })
            self._interviews_table.set_data(interviews_data)

            # Update pipelines needing attention
            attention = metrics_service.get_pipelines_needing_attention(limit=10)
            attention_data = []
            for item in attention:
                attention_data.append({
                    "id": item.id,
                    "company": item.company,
                    "role": item.role[:20] + "..." if len(item.role) > 20 else item.role,
                    "health": item.health.value,
                    "reason": item.reason,
                })
            self._attention_table.set_data(attention_data)

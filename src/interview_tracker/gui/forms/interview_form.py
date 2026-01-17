"""Interview form dialog for scheduling interviews."""

import customtkinter as ctk
from datetime import datetime, date, timedelta
from typing import Callable, Optional, List

from ..theme import Colors, Fonts, Spacing, Dimensions
from ...core.schemas import InterviewCreate, InterviewUpdate
from ...core.enums import PipelineStage, InterviewMode, PrepStatus
from ...services.interview import InterviewService
from ...services.pipeline import PipelineService
from ...data.database import get_db


class InterviewFormDialog(ctk.CTkToplevel):
    """Dialog for scheduling or editing an interview."""

    def __init__(
        self,
        master,
        interview_id: Optional[int] = None,
        pipeline_id: Optional[int] = None,
        on_save: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._interview_id = interview_id
        self._pipeline_id = pipeline_id
        self._on_save = on_save
        self._is_edit = interview_id is not None
        self._pipelines: List[tuple[int, str]] = []

        self.title("Edit Interview" if self._is_edit else "Schedule Interview")
        self.geometry("550x700")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        self._load_pipelines()
        self._create_widgets()

        if self._is_edit:
            self._load_interview()
        elif self._pipeline_id:
            # Pre-select pipeline
            for i, (pid, name) in enumerate(self._pipelines):
                if pid == self._pipeline_id:
                    self._pipeline_dropdown.set(name)
                    break

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _load_pipelines(self):
        """Load active pipelines for dropdown."""
        db = get_db()

        with db.session_scope() as session:
            service = PipelineService(session)
            pipelines = service.get_active()
            self._pipelines = [
                (p.id, f"{p.company} - {p.role[:30]}")
                for p in pipelines
            ]

    def _create_widgets(self):
        """Create form widgets."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Edit Interview" if self._is_edit else "Schedule Interview",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(anchor="w", pady=(0, Spacing.PADDING_LARGE))

        # Scrollable form
        form_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        # Pipeline selection
        self._add_field(form_frame, "Pipeline *")
        pipeline_names = [name for _, name in self._pipelines]
        self._pipeline_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=pipeline_names if pipeline_names else ["No active pipelines"],
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            height=Dimensions.INPUT_HEIGHT,
        )
        self._pipeline_dropdown.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Stage
        self._add_field(form_frame, "Interview Stage *")
        stage_options = [s.display_name for s in PipelineStage if not s.is_terminal]
        self._stage_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=stage_options,
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            height=Dimensions.INPUT_HEIGHT,
        )
        self._stage_dropdown.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Round number
        self._add_field(form_frame, "Round Number")
        self._round_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="1",
        )
        self._round_entry.insert(0, "1")
        self._round_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Date and Time
        self._add_field(form_frame, "Date and Time *")
        datetime_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        datetime_frame.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Date entry (simple text for now)
        self._date_entry = ctk.CTkEntry(
            datetime_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="YYYY-MM-DD",
            width=150,
        )
        self._date_entry.pack(side="left", padx=(0, Spacing.PADDING_SMALL))

        # Time entry
        self._time_entry = ctk.CTkEntry(
            datetime_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="HH:MM",
            width=100,
        )
        self._time_entry.pack(side="left")

        # Duration
        self._add_field(form_frame, "Duration (minutes)")
        self._duration_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._duration_entry.insert(0, "60")
        self._duration_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Mode
        self._add_field(form_frame, "Interview Mode")
        mode_options = [m.display_name for m in InterviewMode]
        self._mode_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=mode_options,
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            height=Dimensions.INPUT_HEIGHT,
        )
        self._mode_dropdown.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Meeting link
        self._add_field(form_frame, "Meeting Link")
        self._link_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="https://...",
        )
        self._link_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Interviewer name
        self._add_field(form_frame, "Interviewer Name")
        self._interviewer_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._interviewer_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Interviewer title
        self._add_field(form_frame, "Interviewer Title")
        self._interviewer_title_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="e.g., Senior Engineer, Engineering Manager",
        )
        self._interviewer_title_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Topics
        self._add_field(form_frame, "Topics to Prepare (comma-separated)")
        self._topics_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="e.g., System Design, Algorithms, Behavioral",
        )
        self._topics_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Prep notes
        self._add_field(form_frame, "Preparation Notes")
        self._prep_notes_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=80,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._prep_notes_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Error label
        self._error_label = ctk.CTkLabel(
            main_frame,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.DANGER,
        )
        self._error_label.pack(pady=(Spacing.PADDING_SMALL, 0))

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(Spacing.PADDING_NORMAL, 0))

        cancel_btn = ctk.CTkButton(
            button_frame,
            text="Cancel",
            font=Fonts.get("normal"),
            fg_color="transparent",
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BG_LIGHT,
            height=Dimensions.BUTTON_HEIGHT,
            command=self.destroy,
        )
        cancel_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            button_frame,
            text="Save",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_save_click,
        )
        save_btn.pack(side="right")

    def _add_field(self, parent, label: str):
        """Add a field label."""
        label_widget = ctk.CTkLabel(
            parent,
            text=label,
            font=Fonts.get("small"),
            text_color=Colors.TEXT_MUTED,
        )
        label_widget.pack(anchor="w")

    def _load_interview(self):
        """Load existing interview data for editing."""
        db = get_db()

        with db.session_scope() as session:
            service = InterviewService(session)
            interview = service.get_with_pipeline(self._interview_id)

            if interview:
                # Set pipeline
                for i, (pid, name) in enumerate(self._pipelines):
                    if pid == interview.pipeline_id:
                        self._pipeline_dropdown.set(name)
                        break

                # Set stage
                stage = PipelineStage(interview.stage)
                self._stage_dropdown.set(stage.display_name)

                # Set round
                self._round_entry.delete(0, "end")
                self._round_entry.insert(0, str(interview.round_number))

                # Set date/time
                if interview.scheduled_date:
                    self._date_entry.insert(0, interview.scheduled_date.strftime("%Y-%m-%d"))
                    self._time_entry.insert(0, interview.scheduled_date.strftime("%H:%M"))

                # Set duration
                self._duration_entry.delete(0, "end")
                self._duration_entry.insert(0, str(interview.duration_minutes))

                # Set mode
                mode = InterviewMode(interview.mode)
                self._mode_dropdown.set(mode.display_name)

                # Set other fields
                if interview.meeting_link:
                    self._link_entry.insert(0, interview.meeting_link)
                if interview.interviewer_name:
                    self._interviewer_entry.insert(0, interview.interviewer_name)
                if interview.interviewer_title:
                    self._interviewer_title_entry.insert(0, interview.interviewer_title)
                if interview.topics:
                    self._topics_entry.insert(0, ", ".join(interview.topics))
                if interview.prep_notes:
                    self._prep_notes_text.insert("1.0", interview.prep_notes)

    def _on_save_click(self):
        """Handle save button click."""
        # Validate pipeline
        pipeline_name = self._pipeline_dropdown.get()
        pipeline_id = None
        for pid, name in self._pipelines:
            if name == pipeline_name:
                pipeline_id = pid
                break

        if not pipeline_id:
            self._error_label.configure(text="Please select a pipeline")
            return

        # Validate stage
        stage_name = self._stage_dropdown.get()
        stage = None
        for s in PipelineStage:
            if s.display_name == stage_name:
                stage = s
                break

        if not stage:
            self._error_label.configure(text="Please select a stage")
            return

        # Validate date/time
        date_str = self._date_entry.get().strip()
        time_str = self._time_entry.get().strip()

        if not date_str or not time_str:
            self._error_label.configure(text="Please enter date and time")
            return

        try:
            scheduled_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        except ValueError:
            self._error_label.configure(text="Invalid date/time format. Use YYYY-MM-DD HH:MM")
            return

        # Get other values
        try:
            round_number = int(self._round_entry.get() or "1")
        except ValueError:
            round_number = 1

        try:
            duration = int(self._duration_entry.get() or "60")
        except ValueError:
            duration = 60

        mode_name = self._mode_dropdown.get()
        mode = InterviewMode.VIDEO
        for m in InterviewMode:
            if m.display_name == mode_name:
                mode = m
                break

        meeting_link = self._link_entry.get().strip() or None
        interviewer_name = self._interviewer_entry.get().strip() or None
        interviewer_title = self._interviewer_title_entry.get().strip() or None

        topics_str = self._topics_entry.get().strip()
        topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else None

        prep_notes = self._prep_notes_text.get("1.0", "end-1c").strip() or None

        db = get_db()

        try:
            with db.session_scope() as session:
                service = InterviewService(session)

                if self._is_edit:
                    service.update(self._interview_id, InterviewUpdate(
                        stage=stage,
                        round_number=round_number,
                        scheduled_date=scheduled_date,
                        duration_minutes=duration,
                        mode=mode,
                        meeting_link=meeting_link,
                        interviewer_name=interviewer_name,
                        interviewer_title=interviewer_title,
                        topics=topics,
                        prep_notes=prep_notes,
                    ))
                else:
                    service.create(InterviewCreate(
                        pipeline_id=pipeline_id,
                        stage=stage,
                        round_number=round_number,
                        scheduled_date=scheduled_date,
                        duration_minutes=duration,
                        mode=mode,
                        meeting_link=meeting_link,
                        interviewer_name=interviewer_name,
                        interviewer_title=interviewer_title,
                        topics=topics,
                        prep_notes=prep_notes,
                    ))

            if self._on_save:
                self._on_save()
            self.destroy()

        except Exception as e:
            self._error_label.configure(text=f"Error: {str(e)}")

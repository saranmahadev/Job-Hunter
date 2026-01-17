"""Pipeline form dialog for adding/editing pipelines."""

import customtkinter as ctk
from datetime import date
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions
from ...core.schemas import PipelineCreate, PipelineUpdate
from ...core.enums import Priority
from ...services.pipeline import PipelineService
from ...data.database import get_db


class PipelineFormDialog(ctk.CTkToplevel):
    """Dialog for adding or editing a pipeline."""

    def __init__(
        self,
        master,
        pipeline_id: Optional[int] = None,
        on_save: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._pipeline_id = pipeline_id
        self._on_save = on_save
        self._is_edit = pipeline_id is not None

        self.title("Edit Pipeline" if self._is_edit else "Add Pipeline")
        self.geometry("500x600")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        self._create_widgets()

        if self._is_edit:
            self._load_pipeline()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create form widgets."""
        # Main container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Edit Pipeline" if self._is_edit else "Add New Pipeline",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(anchor="w", pady=(0, Spacing.PADDING_LARGE))

        # Scrollable form
        form_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        # Company
        self._add_field(form_frame, "Company *")
        self._company_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._company_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Role
        self._add_field(form_frame, "Role / Position *")
        self._role_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._role_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Job URL
        self._add_field(form_frame, "Job Posting URL")
        self._url_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="https://...",
        )
        self._url_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Location
        self._add_field(form_frame, "Location")
        self._location_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="City, State or Remote",
        )
        self._location_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Remote Policy
        self._add_field(form_frame, "Remote Policy")
        self._remote_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=["Not specified", "Remote", "Hybrid", "On-site"],
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            height=Dimensions.INPUT_HEIGHT,
        )
        self._remote_dropdown.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Salary Range
        self._add_field(form_frame, "Salary Range")
        self._salary_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="e.g., $150,000 - $180,000",
        )
        self._salary_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Priority
        self._add_field(form_frame, "Priority")
        priority_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        priority_frame.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._priority_var = ctk.IntVar(value=2)
        for p in Priority:
            rb = ctk.CTkRadioButton(
                priority_frame,
                text=p.display_name,
                variable=self._priority_var,
                value=p.value,
                font=Fonts.get("normal"),
            )
            rb.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Notes
        self._add_field(form_frame, "Notes")
        self._notes_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=100,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._notes_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

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

    def _load_pipeline(self):
        """Load existing pipeline data for editing."""
        db = get_db()

        with db.session_scope() as session:
            service = PipelineService(session)
            pipeline = service.get(self._pipeline_id)

            if pipeline:
                self._company_entry.insert(0, pipeline.company)
                self._role_entry.insert(0, pipeline.role)
                if pipeline.job_url:
                    self._url_entry.insert(0, pipeline.job_url)
                if pipeline.location:
                    self._location_entry.insert(0, pipeline.location)
                if pipeline.remote_policy:
                    self._remote_dropdown.set(pipeline.remote_policy)
                if pipeline.salary_range:
                    self._salary_entry.insert(0, pipeline.salary_range)
                self._priority_var.set(pipeline.priority)
                if pipeline.notes:
                    self._notes_text.insert("1.0", pipeline.notes)

    def _on_save_click(self):
        """Handle save button click."""
        # Validate
        company = self._company_entry.get().strip()
        role = self._role_entry.get().strip()

        if not company:
            self._error_label.configure(text="Company is required")
            return
        if not role:
            self._error_label.configure(text="Role is required")
            return

        # Gather data
        url = self._url_entry.get().strip() or None
        location = self._location_entry.get().strip() or None
        remote = self._remote_dropdown.get()
        if remote == "Not specified":
            remote = None
        salary = self._salary_entry.get().strip() or None
        priority = self._priority_var.get()
        notes = self._notes_text.get("1.0", "end-1c").strip() or None

        db = get_db()

        try:
            with db.session_scope() as session:
                service = PipelineService(session)

                if self._is_edit:
                    service.update(self._pipeline_id, PipelineUpdate(
                        company=company,
                        role=role,
                        job_url=url,
                        location=location,
                        remote_policy=remote,
                        salary_range=salary,
                        priority=priority,
                        notes=notes,
                    ))
                else:
                    service.create(PipelineCreate(
                        company=company,
                        role=role,
                        job_url=url,
                        location=location,
                        remote_policy=remote,
                        salary_range=salary,
                        priority=priority,
                        notes=notes,
                    ))

            if self._on_save:
                self._on_save()
            self.destroy()

        except Exception as e:
            self._error_label.configure(text=f"Error: {str(e)}")

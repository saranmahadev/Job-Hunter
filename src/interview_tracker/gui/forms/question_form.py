"""Question form dialog for adding/editing questions."""

import customtkinter as ctk
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions
from ...core.schemas import QuestionCreate, QuestionUpdate
from ...core.enums import QuestionType
from ...services.questions import QuestionService
from ...data.database import get_db


class QuestionFormDialog(ctk.CTkToplevel):
    """Dialog for adding or editing a question."""

    def __init__(
        self,
        master,
        question_id: Optional[int] = None,
        interview_id: Optional[int] = None,
        on_save: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(master, **kwargs)

        self._question_id = question_id
        self._interview_id = interview_id
        self._on_save = on_save
        self._is_edit = question_id is not None

        self.title("Edit Question" if self._is_edit else "Add Question")
        self.geometry("550x650")
        self.resizable(False, False)

        # Make modal
        self.transient(master)
        self.grab_set()

        self._create_widgets()

        if self._is_edit:
            self._load_question()

        # Center on parent
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_y() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        """Create form widgets."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Edit Question" if self._is_edit else "Add Question",
            font=Fonts.get("large", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(anchor="w", pady=(0, Spacing.PADDING_LARGE))

        # Scrollable form
        form_frame = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        form_frame.pack(fill="both", expand=True)

        # Question text
        self._add_field(form_frame, "Question *")
        self._question_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=80,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._question_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Question type
        self._add_field(form_frame, "Question Type")
        type_options = [qt.display_name for qt in QuestionType]
        self._type_dropdown = ctk.CTkOptionMenu(
            form_frame,
            values=type_options,
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            height=Dimensions.INPUT_HEIGHT,
        )
        self._type_dropdown.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # My answer
        self._add_field(form_frame, "My Answer")
        self._answer_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=100,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._answer_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Ideal answer
        self._add_field(form_frame, "Ideal / Expected Answer")
        self._ideal_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=100,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._ideal_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Self-rating
        self._add_field(form_frame, "Self Rating (1-5)")
        rating_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        rating_frame.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._rating_var = ctk.IntVar(value=0)
        for i in range(1, 6):
            rb = ctk.CTkRadioButton(
                rating_frame,
                text=str(i),
                variable=self._rating_var,
                value=i,
                font=Fonts.get("normal"),
            )
            rb.pack(side="left", padx=Spacing.PADDING_SMALL)

        # None option for rating
        none_rb = ctk.CTkRadioButton(
            rating_frame,
            text="N/A",
            variable=self._rating_var,
            value=0,
            font=Fonts.get("normal"),
        )
        none_rb.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Gap identified
        self._add_field(form_frame, "Gap Identified")
        self._gap_text = ctk.CTkTextbox(
            form_frame,
            font=Fonts.get("normal"),
            height=60,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
        )
        self._gap_text.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Action item
        self._add_field(form_frame, "Action Item")
        self._action_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="What will you do to improve?",
        )
        self._action_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        # Tags
        self._add_field(form_frame, "Tags (comma-separated)")
        self._tags_entry = ctk.CTkEntry(
            form_frame,
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            placeholder_text="e.g., algorithms, dynamic-programming, graphs",
        )
        self._tags_entry.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

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

    def _load_question(self):
        """Load existing question data for editing."""
        db = get_db()

        with db.session_scope() as session:
            service = QuestionService(session)
            question = service.get(self._question_id)

            if question:
                self._question_text.insert("1.0", question.question_text)

                qtype = QuestionType(question.question_type)
                self._type_dropdown.set(qtype.display_name)

                if question.my_answer:
                    self._answer_text.insert("1.0", question.my_answer)
                if question.ideal_answer:
                    self._ideal_text.insert("1.0", question.ideal_answer)
                if question.rating:
                    self._rating_var.set(question.rating)
                if question.gap_identified:
                    self._gap_text.insert("1.0", question.gap_identified)
                if question.action_item:
                    self._action_entry.insert(0, question.action_item)
                if question.tags:
                    self._tags_entry.insert(0, ", ".join(question.tags))

    def _on_save_click(self):
        """Handle save button click."""
        # Validate
        question_text = self._question_text.get("1.0", "end-1c").strip()

        if not question_text:
            self._error_label.configure(text="Question text is required")
            return

        # Get question type
        type_name = self._type_dropdown.get()
        question_type = QuestionType.OTHER
        for qt in QuestionType:
            if qt.display_name == type_name:
                question_type = qt
                break

        # Get other values
        my_answer = self._answer_text.get("1.0", "end-1c").strip() or None
        ideal_answer = self._ideal_text.get("1.0", "end-1c").strip() or None
        rating = self._rating_var.get() if self._rating_var.get() > 0 else None
        gap = self._gap_text.get("1.0", "end-1c").strip() or None
        action = self._action_entry.get().strip() or None

        tags_str = self._tags_entry.get().strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        db = get_db()

        try:
            with db.session_scope() as session:
                service = QuestionService(session)

                if self._is_edit:
                    service.update(self._question_id, QuestionUpdate(
                        question_text=question_text,
                        question_type=question_type,
                        my_answer=my_answer,
                        ideal_answer=ideal_answer,
                        rating=rating,
                        gap_identified=gap,
                        action_item=action,
                        tags=tags,
                    ))
                else:
                    service.create(QuestionCreate(
                        interview_id=self._interview_id,
                        question_text=question_text,
                        question_type=question_type,
                        my_answer=my_answer,
                        ideal_answer=ideal_answer,
                        rating=rating,
                        gap_identified=gap,
                        action_item=action,
                        tags=tags,
                    ))

            if self._on_save:
                self._on_save()
            self.destroy()

        except Exception as e:
            self._error_label.configure(text=f"Error: {str(e)}")

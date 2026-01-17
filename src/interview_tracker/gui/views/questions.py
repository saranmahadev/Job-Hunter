"""Question bank view for tracking interview questions."""

import customtkinter as ctk
from typing import Callable, Optional

from ..theme import Colors, Fonts, Spacing, Dimensions
from ..components.data_table import DataTable, StatusBadge
from ...services.questions import QuestionService
from ...core.enums import QuestionType
from ...data.database import get_db


class QuestionBankView(ctk.CTkFrame):
    """View for the question bank."""

    def __init__(
        self,
        master,
        on_add_question: Optional[Callable[[], None]] = None,
        on_view_question: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._on_add_question = on_add_question
        self._on_view_question = on_view_question
        self._filter_type: Optional[QuestionType] = None

        self._create_widgets()
        self.refresh()

    def _create_widgets(self):
        """Create question bank widgets."""
        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        title = ctk.CTkLabel(
            header_frame,
            text="Question Bank",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left")

        add_btn = ctk.CTkButton(
            header_frame,
            text="+ Add Question",
            font=Fonts.get("normal"),
            fg_color=Colors.PRIMARY,
            hover_color=Colors.PRIMARY_HOVER,
            height=Dimensions.BUTTON_HEIGHT,
            corner_radius=Dimensions.BUTTON_CORNER_RADIUS,
            command=self._on_add_click,
        )
        add_btn.pack(side="right")

        # Filter and search
        filter_frame = ctk.CTkFrame(self, fg_color="transparent")
        filter_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_NORMAL))

        # Type filter dropdown
        ctk.CTkLabel(filter_frame, text="Type:", font=Fonts.get("normal"), text_color=Colors.TEXT_SECONDARY).pack(side="left")

        type_options = ["All Types"] + [qt.display_name for qt in QuestionType]
        self._type_dropdown = ctk.CTkOptionMenu(
            filter_frame,
            values=type_options,
            font=Fonts.get("normal"),
            fg_color=Colors.BG_CARD,
            button_color=Colors.PRIMARY,
            button_hover_color=Colors.PRIMARY_HOVER,
            command=self._on_type_filter_change,
        )
        self._type_dropdown.pack(side="left", padx=Spacing.PADDING_SMALL)

        # Search
        self._search_entry = ctk.CTkEntry(
            filter_frame,
            placeholder_text="Search questions...",
            font=Fonts.get("normal"),
            height=Dimensions.INPUT_HEIGHT,
            corner_radius=Dimensions.INPUT_CORNER_RADIUS,
            width=250,
        )
        self._search_entry.pack(side="left", padx=Spacing.PADDING_NORMAL)
        self._search_entry.bind("<Return>", lambda e: self._on_search())

        search_btn = ctk.CTkButton(
            filter_frame,
            text="Search",
            font=Fonts.get("normal"),
            fg_color=Colors.SECONDARY,
            height=Dimensions.INPUT_HEIGHT,
            width=80,
            command=self._on_search,
        )
        search_btn.pack(side="left")

        # Stats row
        stats_frame = ctk.CTkFrame(self, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        stats_frame.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_NORMAL))

        stats_inner = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_inner.pack(padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_NORMAL)

        self._stats_labels = {}
        stats = [
            ("total", "Total Questions"),
            ("gaps", "With Gaps"),
            ("actions", "Action Items"),
            ("low_rated", "Low Rated"),
        ]

        for key, label in stats:
            stat_frame = ctk.CTkFrame(stats_inner, fg_color="transparent")
            stat_frame.pack(side="left", padx=Spacing.PADDING_LARGE)

            value_label = ctk.CTkLabel(
                stat_frame,
                text="0",
                font=Fonts.get("large", "bold"),
                text_color=Colors.TEXT_PRIMARY,
            )
            value_label.pack()

            name_label = ctk.CTkLabel(
                stat_frame,
                text=label,
                font=Fonts.get("small"),
                text_color=Colors.TEXT_MUTED,
            )
            name_label.pack()

            self._stats_labels[key] = value_label

        # Table
        self._table = DataTable(
            self,
            columns=[
                {"key": "question", "title": "Question", "width": 350},
                {"key": "type", "title": "Type", "width": 100,
                 "render": self._render_type},
                {"key": "rating", "title": "Rating", "width": 80,
                 "render": self._render_rating},
                {"key": "has_gap", "title": "Gap", "width": 60, "align": "center"},
                {"key": "has_action", "title": "Action", "width": 60, "align": "center"},
            ],
            on_row_double_click=self._on_row_double_click,
        )
        self._table.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE, pady=(0, Spacing.PADDING_LARGE))

    def _render_type(self, parent, value, row_data):
        """Render question type as badge."""
        type_colors = {
            "behavioral": Colors.INFO,
            "technical": Colors.PRIMARY,
            "system_design": Colors.SUCCESS,
            "coding": Colors.WARNING,
            "culture": Colors.DANGER_LIGHT,
            "other": Colors.TEXT_MUTED,
        }
        color = type_colors.get(value, Colors.TEXT_MUTED)
        text = value.replace("_", " ").title()
        return StatusBadge(parent, text=text, color=color)

    def _render_rating(self, parent, value, row_data):
        """Render rating as stars."""
        if value is None:
            text = "-"
            color = Colors.TEXT_MUTED
        else:
            text = "\u2605" * value
            if value <= 2:
                color = Colors.DANGER
            elif value <= 3:
                color = Colors.WARNING
            else:
                color = Colors.SUCCESS

        label = ctk.CTkLabel(
            parent,
            text=text,
            font=Fonts.get("normal"),
            text_color=color,
        )
        return label

    def _on_add_click(self):
        if self._on_add_question:
            self._on_add_question()

    def _on_type_filter_change(self, value: str):
        """Handle type filter change."""
        if value == "All Types":
            self._filter_type = None
        else:
            # Find matching enum
            for qt in QuestionType:
                if qt.display_name == value:
                    self._filter_type = qt
                    break
        self.refresh()

    def _on_search(self):
        """Handle search."""
        query = self._search_entry.get().strip()
        self.refresh(search_query=query)

    def _on_row_double_click(self, index: int, row_data: dict):
        if self._on_view_question and "id" in row_data:
            self._on_view_question(row_data["id"])

    def refresh(self, search_query: Optional[str] = None):
        """Refresh the question bank."""
        db = get_db()

        with db.session_scope() as session:
            question_service = QuestionService(session)

            # Get questions based on filters
            if search_query:
                questions = question_service.search(search_query)
            elif self._filter_type:
                questions = question_service.get_by_type(self._filter_type)
            else:
                questions = question_service.get_all()

            # Update stats
            all_questions = question_service.get_all()
            self._stats_labels["total"].configure(text=str(len(all_questions)))
            self._stats_labels["gaps"].configure(text=str(len(question_service.get_with_gaps())))
            self._stats_labels["actions"].configure(text=str(len(question_service.get_with_action_items())))
            self._stats_labels["low_rated"].configure(text=str(len(question_service.get_low_rated())))

            # Update table
            table_data = []
            for q in questions:
                question_text = q.question_text
                if len(question_text) > 60:
                    question_text = question_text[:60] + "..."

                table_data.append({
                    "id": q.id,
                    "question": question_text,
                    "type": q.question_type,
                    "rating": q.rating,
                    "has_gap": "\u2713" if q.gap_identified else "",
                    "has_action": "\u2713" if q.action_item else "",
                })

            self._table.set_data(table_data)


class QuestionDetailView(ctk.CTkFrame):
    """View for displaying question details."""

    def __init__(
        self,
        master,
        question_id: int,
        on_back: Optional[Callable[[], None]] = None,
        on_edit: Optional[Callable[[int], None]] = None,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._question_id = question_id
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

        title = ctk.CTkLabel(
            header_frame,
            text="Question Details",
            font=Fonts.get("title", "bold"),
            text_color=Colors.TEXT_PRIMARY,
        )
        title.pack(side="left", padx=Spacing.PADDING_LARGE)

        edit_btn = ctk.CTkButton(
            header_frame,
            text="Edit",
            font=Fonts.get("normal"),
            fg_color=Colors.SECONDARY,
            height=Dimensions.BUTTON_HEIGHT,
            command=self._on_edit_click,
        )
        edit_btn.pack(side="right")

        # Content
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.PADDING_LARGE)

        # Question card
        question_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        question_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        question_inner = ctk.CTkFrame(question_card, fg_color="transparent")
        question_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Type and rating row
        meta_frame = ctk.CTkFrame(question_inner, fg_color="transparent")
        meta_frame.pack(fill="x", pady=(0, Spacing.PADDING_NORMAL))

        self._type_badge = ctk.CTkFrame(meta_frame, fg_color=Colors.PRIMARY, corner_radius=4)
        self._type_badge.pack(side="left")
        self._type_label = ctk.CTkLabel(self._type_badge, text="-", font=Fonts.get("small"))
        self._type_label.pack(padx=Spacing.PADDING_SMALL, pady=2)

        self._rating_label = ctk.CTkLabel(
            meta_frame,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.WARNING,
        )
        self._rating_label.pack(side="left", padx=Spacing.PADDING_NORMAL)

        # Question text
        ctk.CTkLabel(question_inner, text="Question:", font=Fonts.get("small"), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self._question_label = ctk.CTkLabel(
            question_inner,
            text="",
            font=Fonts.get("medium"),
            text_color=Colors.TEXT_PRIMARY,
            wraplength=600,
            justify="left",
        )
        self._question_label.pack(anchor="w", pady=(0, Spacing.PADDING_NORMAL))

        # My answer
        ctk.CTkLabel(question_inner, text="My Answer:", font=Fonts.get("small"), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self._answer_label = ctk.CTkLabel(
            question_inner,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.TEXT_PRIMARY,
            wraplength=600,
            justify="left",
        )
        self._answer_label.pack(anchor="w", pady=(0, Spacing.PADDING_NORMAL))

        # Ideal answer
        ctk.CTkLabel(question_inner, text="Ideal Answer:", font=Fonts.get("small"), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self._ideal_label = ctk.CTkLabel(
            question_inner,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.SUCCESS,
            wraplength=600,
            justify="left",
        )
        self._ideal_label.pack(anchor="w")

        # Gap and Action card
        gap_card = ctk.CTkFrame(content, fg_color=Colors.BG_CARD, corner_radius=Dimensions.CARD_CORNER_RADIUS)
        gap_card.pack(fill="x", pady=Spacing.PADDING_NORMAL)

        gap_inner = ctk.CTkFrame(gap_card, fg_color="transparent")
        gap_inner.pack(fill="x", padx=Spacing.PADDING_LARGE, pady=Spacing.PADDING_LARGE)

        # Gap identified
        ctk.CTkLabel(gap_inner, text="Gap Identified:", font=Fonts.get("small"), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self._gap_label = ctk.CTkLabel(
            gap_inner,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.DANGER_LIGHT,
            wraplength=600,
            justify="left",
        )
        self._gap_label.pack(anchor="w", pady=(0, Spacing.PADDING_NORMAL))

        # Action item
        ctk.CTkLabel(gap_inner, text="Action Item:", font=Fonts.get("small"), text_color=Colors.TEXT_MUTED).pack(anchor="w")
        self._action_label = ctk.CTkLabel(
            gap_inner,
            text="",
            font=Fonts.get("normal"),
            text_color=Colors.WARNING,
            wraplength=600,
            justify="left",
        )
        self._action_label.pack(anchor="w")

    def _on_back_click(self):
        if self._on_back:
            self._on_back()

    def _on_edit_click(self):
        if self._on_edit:
            self._on_edit(self._question_id)

    def refresh(self):
        """Refresh question details."""
        db = get_db()

        with db.session_scope() as session:
            question_service = QuestionService(session)
            question = question_service.get(self._question_id)

            if not question:
                return

            # Update type badge
            qtype = QuestionType(question.question_type)
            self._type_label.configure(text=qtype.display_name)

            # Update rating
            if question.rating:
                stars = "\u2605" * question.rating + "\u2606" * (5 - question.rating)
                self._rating_label.configure(text=stars)
            else:
                self._rating_label.configure(text="Not rated")

            # Update texts
            self._question_label.configure(text=question.question_text)
            self._answer_label.configure(text=question.my_answer or "No answer recorded")
            self._ideal_label.configure(text=question.ideal_answer or "No ideal answer specified")
            self._gap_label.configure(text=question.gap_identified or "No gap identified")
            self._action_label.configure(text=question.action_item or "No action item")

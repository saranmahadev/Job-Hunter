"""Main application window for Interview Tracker."""

import customtkinter as ctk
from typing import Optional

from .theme import Colors, Fonts, Dimensions
from .components.sidebar import Sidebar
from .views.dashboard import DashboardView
from .views.pipelines import PipelineListView, PipelineDetailView
from .views.interviews import InterviewListView, InterviewDetailView
from .views.questions import QuestionBankView, QuestionDetailView
from .forms.pipeline_form import PipelineFormDialog
from .forms.interview_form import InterviewFormDialog
from .forms.question_form import QuestionFormDialog


class InterviewTrackerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("Interview Tracker")
        self.geometry(f"{Dimensions.WINDOW_DEFAULT_WIDTH}x{Dimensions.WINDOW_DEFAULT_HEIGHT}")
        self.minsize(Dimensions.WINDOW_MIN_WIDTH, Dimensions.WINDOW_MIN_HEIGHT)

        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Current view tracking
        self._current_view: Optional[ctk.CTkFrame] = None
        self._view_stack: list = []

        # Create main layout
        self._create_layout()

        # Show dashboard by default
        self._show_dashboard()

    def _create_layout(self):
        """Create the main application layout."""
        # Sidebar
        self._sidebar = Sidebar(
            self,
            on_navigate=self._on_navigate,
        )
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        # Main content area
        self._content_frame = ctk.CTkFrame(
            self,
            fg_color=Colors.BG_DARK,
            corner_radius=0,
        )
        self._content_frame.grid(row=0, column=1, sticky="nsew")
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._content_frame.grid_rowconfigure(0, weight=1)

    def _on_navigate(self, view_id: str):
        """Handle navigation from sidebar."""
        # Clear view stack when navigating via sidebar
        self._view_stack.clear()

        if view_id == "dashboard":
            self._show_dashboard()
        elif view_id == "pipelines":
            self._show_pipelines()
        elif view_id == "interviews":
            self._show_interviews()
        elif view_id == "questions":
            self._show_questions()
        elif view_id == "settings":
            self._show_settings()

    def _switch_view(self, new_view: ctk.CTkFrame):
        """Switch to a new view."""
        if self._current_view:
            self._current_view.destroy()

        self._current_view = new_view
        self._current_view.grid(row=0, column=0, sticky="nsew")

    def _push_view(self, new_view: ctk.CTkFrame):
        """Push a new view onto the stack (for detail views)."""
        if self._current_view:
            self._view_stack.append(self._current_view)
            self._current_view.grid_forget()

        self._current_view = new_view
        self._current_view.grid(row=0, column=0, sticky="nsew")

    def _pop_view(self):
        """Pop back to the previous view."""
        if self._view_stack:
            if self._current_view:
                self._current_view.destroy()

            self._current_view = self._view_stack.pop()
            self._current_view.grid(row=0, column=0, sticky="nsew")

            # Refresh the view if it has a refresh method
            if hasattr(self._current_view, 'refresh'):
                self._current_view.refresh()

    # =========================================================================
    # Dashboard
    # =========================================================================

    def _show_dashboard(self):
        """Show the dashboard view."""
        view = DashboardView(
            self._content_frame,
            on_view_pipeline=self._show_pipeline_detail,
            on_view_interview=self._show_interview_detail,
            on_add_pipeline=self._show_add_pipeline_dialog,
            on_schedule_interview=self._show_schedule_interview_dialog,
        )
        self._switch_view(view)

    # =========================================================================
    # Pipelines
    # =========================================================================

    def _show_pipelines(self):
        """Show the pipelines list view."""
        view = PipelineListView(
            self._content_frame,
            on_view_pipeline=self._show_pipeline_detail,
            on_add_pipeline=self._show_add_pipeline_dialog,
        )
        self._switch_view(view)

    def _show_pipeline_detail(self, pipeline_id: int):
        """Show pipeline detail view."""
        view = PipelineDetailView(
            self._content_frame,
            pipeline_id=pipeline_id,
            on_back=self._pop_view,
            on_schedule_interview=lambda pid: self._show_schedule_interview_dialog(pid),
            on_edit=self._show_edit_pipeline_dialog,
        )
        self._push_view(view)

    def _show_add_pipeline_dialog(self):
        """Show dialog to add a new pipeline."""
        PipelineFormDialog(
            self,
            on_save=self._refresh_current_view,
        )

    def _show_edit_pipeline_dialog(self, pipeline_id: int):
        """Show dialog to edit a pipeline."""
        PipelineFormDialog(
            self,
            pipeline_id=pipeline_id,
            on_save=self._refresh_current_view,
        )

    # =========================================================================
    # Interviews
    # =========================================================================

    def _show_interviews(self):
        """Show the interviews list view."""
        view = InterviewListView(
            self._content_frame,
            on_view_interview=self._show_interview_detail,
            on_schedule_interview=self._show_schedule_interview_dialog,
        )
        self._switch_view(view)

    def _show_interview_detail(self, interview_id: int):
        """Show interview detail view."""
        view = InterviewDetailView(
            self._content_frame,
            interview_id=interview_id,
            on_back=self._pop_view,
            on_edit=self._show_edit_interview_dialog,
        )
        self._push_view(view)

    def _show_schedule_interview_dialog(self, pipeline_id: Optional[int] = None):
        """Show dialog to schedule a new interview."""
        InterviewFormDialog(
            self,
            pipeline_id=pipeline_id,
            on_save=self._refresh_current_view,
        )

    def _show_edit_interview_dialog(self, interview_id: int):
        """Show dialog to edit an interview."""
        InterviewFormDialog(
            self,
            interview_id=interview_id,
            on_save=self._refresh_current_view,
        )

    # =========================================================================
    # Questions
    # =========================================================================

    def _show_questions(self):
        """Show the question bank view."""
        view = QuestionBankView(
            self._content_frame,
            on_add_question=self._show_add_question_dialog,
            on_view_question=self._show_question_detail,
        )
        self._switch_view(view)

    def _show_question_detail(self, question_id: int):
        """Show question detail view."""
        view = QuestionDetailView(
            self._content_frame,
            question_id=question_id,
            on_back=self._pop_view,
            on_edit=self._show_edit_question_dialog,
        )
        self._push_view(view)

    def _show_add_question_dialog(self):
        """Show dialog to add a new question."""
        QuestionFormDialog(
            self,
            on_save=self._refresh_current_view,
        )

    def _show_edit_question_dialog(self, question_id: int):
        """Show dialog to edit a question."""
        QuestionFormDialog(
            self,
            question_id=question_id,
            on_save=self._refresh_current_view,
        )

    # =========================================================================
    # Settings
    # =========================================================================

    def _show_settings(self):
        """Show the settings view."""
        from .views.settings import SettingsView
        view = SettingsView(self._content_frame)
        self._switch_view(view)

    # =========================================================================
    # Utilities
    # =========================================================================

    def _refresh_current_view(self):
        """Refresh the current view if it supports it."""
        if self._current_view and hasattr(self._current_view, 'refresh'):
            self._current_view.refresh()


def run_app():
    """Run the Interview Tracker application."""
    app = InterviewTrackerApp()
    app.mainloop()

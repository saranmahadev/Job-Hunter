"""Pydantic schemas for validation and data transfer."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, computed_field

from .enums import (
    PipelineStage, InterviewMode, InterviewOutcome, PrepStatus,
    PipelineHealth, QuestionType, PrepCategory, Priority
)


# ============================================================================
# Pipeline Schemas
# ============================================================================

class PipelineCreate(BaseModel):
    """Schema for creating a new pipeline."""
    company: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=200)
    job_url: Optional[str] = None
    applied_date: date = Field(default_factory=date.today)
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None
    notes: Optional[str] = None
    priority: int = Field(default=Priority.MEDIUM.value, ge=1, le=5)


class PipelineUpdate(BaseModel):
    """Schema for updating a pipeline."""
    company: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=200)
    job_url: Optional[str] = None
    current_stage: Optional[PipelineStage] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote_policy: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)


class PipelineRead(BaseModel):
    """Schema for reading a pipeline."""
    id: int
    company: str
    role: str
    job_url: Optional[str]
    current_stage: str
    applied_date: date
    salary_range: Optional[str]
    location: Optional[str]
    remote_policy: Optional[str]
    notes: Optional[str]
    priority: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage(self.current_stage)

    @computed_field
    @property
    def days_since_applied(self) -> int:
        return (date.today() - self.applied_date).days

    @computed_field
    @property
    def days_since_update(self) -> int:
        return (datetime.utcnow() - self.updated_at).days

    model_config = {"from_attributes": True}


# ============================================================================
# Interview Schemas
# ============================================================================

class InterviewCreate(BaseModel):
    """Schema for creating a new interview."""
    pipeline_id: int
    stage: PipelineStage
    round_number: int = 1
    scheduled_date: Optional[datetime] = None
    duration_minutes: int = 60
    mode: InterviewMode = InterviewMode.VIDEO
    meeting_link: Optional[str] = None
    interviewer_name: Optional[str] = None
    interviewer_title: Optional[str] = None
    interviewer_linkedin: Optional[str] = None
    topics: Optional[List[str]] = None
    projects_to_pitch: Optional[List[str]] = None
    prep_notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    """Schema for updating an interview."""
    stage: Optional[PipelineStage] = None
    round_number: Optional[int] = None
    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    mode: Optional[InterviewMode] = None
    meeting_link: Optional[str] = None
    interviewer_name: Optional[str] = None
    interviewer_title: Optional[str] = None
    interviewer_linkedin: Optional[str] = None
    topics: Optional[List[str]] = None
    projects_to_pitch: Optional[List[str]] = None
    prep_status: Optional[PrepStatus] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)
    prep_notes: Optional[str] = None
    outcome: Optional[InterviewOutcome] = None
    feedback_received: Optional[str] = None
    self_assessment: Optional[str] = None
    next_actions: Optional[str] = None
    follow_up_date: Optional[date] = None
    thank_you_sent: Optional[bool] = None


class InterviewRead(BaseModel):
    """Schema for reading an interview."""
    id: int
    pipeline_id: int
    stage: str
    round_number: int
    scheduled_date: Optional[datetime]
    duration_minutes: int
    mode: str
    meeting_link: Optional[str]
    interviewer_name: Optional[str]
    interviewer_title: Optional[str]
    interviewer_linkedin: Optional[str]
    prep_status: str
    confidence: Optional[int]
    prep_notes: Optional[str]
    outcome: str
    feedback_received: Optional[str]
    self_assessment: Optional[str]
    next_actions: Optional[str]
    follow_up_date: Optional[date]
    thank_you_sent: bool
    created_at: datetime
    completed_at: Optional[datetime]

    @computed_field
    @property
    def interview_stage(self) -> PipelineStage:
        return PipelineStage(self.stage)

    @computed_field
    @property
    def interview_mode(self) -> InterviewMode:
        return InterviewMode(self.mode)

    @computed_field
    @property
    def interview_outcome(self) -> InterviewOutcome:
        return InterviewOutcome(self.outcome)

    @computed_field
    @property
    def preparation_status(self) -> PrepStatus:
        return PrepStatus(self.prep_status)

    @computed_field
    @property
    def is_upcoming(self) -> bool:
        if self.scheduled_date:
            return self.scheduled_date > datetime.utcnow()
        return False

    @computed_field
    @property
    def days_until(self) -> Optional[int]:
        if self.scheduled_date:
            delta = self.scheduled_date.date() - date.today()
            return delta.days
        return None

    model_config = {"from_attributes": True}


# ============================================================================
# Contact Schemas
# ============================================================================

class ContactCreate(BaseModel):
    """Schema for creating a contact."""
    pipeline_id: int
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    """Schema for updating a contact."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    notes: Optional[str] = None


class ContactRead(BaseModel):
    """Schema for reading a contact."""
    id: int
    pipeline_id: int
    name: str
    role: str
    email: Optional[str]
    phone: Optional[str]
    linkedin: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Question Schemas
# ============================================================================

class QuestionCreate(BaseModel):
    """Schema for creating an interview question."""
    interview_id: Optional[int] = None
    question_text: str = Field(..., min_length=1)
    question_type: QuestionType = QuestionType.OTHER
    my_answer: Optional[str] = None
    ideal_answer: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    gap_identified: Optional[str] = None
    action_item: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""
    question_text: Optional[str] = Field(None, min_length=1)
    question_type: Optional[QuestionType] = None
    my_answer: Optional[str] = None
    ideal_answer: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    gap_identified: Optional[str] = None
    action_item: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionRead(BaseModel):
    """Schema for reading a question."""
    id: int
    interview_id: Optional[int]
    question_text: str
    question_type: str
    my_answer: Optional[str]
    ideal_answer: Optional[str]
    rating: Optional[int]
    gap_identified: Optional[str]
    action_item: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ============================================================================
# Dashboard / Metrics Schemas
# ============================================================================

class DashboardMetrics(BaseModel):
    """Aggregated metrics for the dashboard."""
    total_active_pipelines: int
    total_interviews_completed: int
    interviews_this_week: int
    pass_rate: float
    average_confidence: float
    pending_follow_ups: int
    offers_received: int
    rejections: int
    avg_days_in_pipeline: float
    stage_distribution: dict[str, int]


class UpcomingInterview(BaseModel):
    """Simplified view of an upcoming interview for dashboard."""
    id: int
    company: str
    role: str
    stage: str
    scheduled_date: datetime
    prep_status: str
    days_until: int

    @computed_field
    @property
    def prep_status_enum(self) -> PrepStatus:
        return PrepStatus(self.prep_status)


class PipelineAttention(BaseModel):
    """Pipeline needing attention for dashboard."""
    id: int
    company: str
    role: str
    current_stage: str
    health: PipelineHealth
    days_since_update: int
    reason: str

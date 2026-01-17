"""SQLAlchemy ORM models for Interview Tracker."""

from datetime import datetime, date
from typing import Optional, List
import json

from sqlalchemy import (
    String, Integer, Text, DateTime, Date, ForeignKey,
    Boolean, create_engine, event
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, Session
)

from .enums import (
    PipelineStage, InterviewMode, InterviewOutcome, PrepStatus,
    QuestionType, PrepCategory, Priority
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class Pipeline(Base):
    """A job application pipeline - one per company/role combination."""
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(200))
    job_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    current_stage: Mapped[str] = mapped_column(
        String(50), default=PipelineStage.APPLIED.value
    )
    applied_date: Mapped[date] = mapped_column(Date, default=date.today)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    remote_policy: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=Priority.MEDIUM.value)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    interviews: Mapped[List["Interview"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan",
        order_by="Interview.scheduled_date"
    )
    contacts: Mapped[List["Contact"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )

    @property
    def stage(self) -> PipelineStage:
        """Get the current stage as an enum."""
        return PipelineStage(self.current_stage)

    @stage.setter
    def stage(self, value: PipelineStage):
        """Set the current stage from an enum."""
        self.current_stage = value.value

    @property
    def days_since_applied(self) -> int:
        """Days since the application was submitted."""
        return (date.today() - self.applied_date).days

    @property
    def days_since_update(self) -> int:
        """Days since the pipeline was last updated."""
        return (datetime.utcnow() - self.updated_at).days

    def __repr__(self) -> str:
        return f"<Pipeline {self.id}: {self.company} - {self.role}>"


class Interview(Base):
    """Individual interview within a pipeline."""
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"))

    # Interview details
    stage: Mapped[str] = mapped_column(String(50))
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    mode: Mapped[str] = mapped_column(String(20), default=InterviewMode.VIDEO.value)
    meeting_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Interviewer info
    interviewer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interviewer_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    interviewer_linkedin: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # Preparation - stored as JSON strings
    _topics: Mapped[Optional[str]] = mapped_column("topics", Text, nullable=True)
    _projects_to_pitch: Mapped[Optional[str]] = mapped_column("projects_to_pitch", Text, nullable=True)
    prep_status: Mapped[str] = mapped_column(String(20), default=PrepStatus.NOT_STARTED.value)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prep_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Results
    outcome: Mapped[str] = mapped_column(String(20), default=InterviewOutcome.PENDING.value)
    feedback_received: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    self_assessment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Follow-up
    next_actions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    thank_you_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship(back_populates="interviews")
    questions: Mapped[List["InterviewQuestion"]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )

    @property
    def topics(self) -> List[str]:
        """Get topics as a list."""
        if self._topics:
            return json.loads(self._topics)
        return []

    @topics.setter
    def topics(self, value: List[str]):
        """Set topics from a list."""
        self._topics = json.dumps(value) if value else None

    @property
    def projects_to_pitch(self) -> List[str]:
        """Get projects as a list."""
        if self._projects_to_pitch:
            return json.loads(self._projects_to_pitch)
        return []

    @projects_to_pitch.setter
    def projects_to_pitch(self, value: List[str]):
        """Set projects from a list."""
        self._projects_to_pitch = json.dumps(value) if value else None

    @property
    def interview_stage(self) -> PipelineStage:
        """Get stage as enum."""
        return PipelineStage(self.stage)

    @property
    def interview_mode(self) -> InterviewMode:
        """Get mode as enum."""
        return InterviewMode(self.mode)

    @property
    def interview_outcome(self) -> InterviewOutcome:
        """Get outcome as enum."""
        return InterviewOutcome(self.outcome)

    @property
    def preparation_status(self) -> PrepStatus:
        """Get prep status as enum."""
        return PrepStatus(self.prep_status)

    @property
    def is_upcoming(self) -> bool:
        """Check if interview is in the future."""
        if self.scheduled_date:
            return self.scheduled_date > datetime.utcnow()
        return False

    @property
    def days_until(self) -> Optional[int]:
        """Days until the interview (negative if past)."""
        if self.scheduled_date:
            delta = self.scheduled_date.date() - date.today()
            return delta.days
        return None

    def __repr__(self) -> str:
        return f"<Interview {self.id}: {self.stage} for Pipeline {self.pipeline_id}>"


class Contact(Base):
    """People associated with a pipeline (recruiters, hiring managers)."""
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id"))

    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="contacts")

    def __repr__(self) -> str:
        return f"<Contact {self.id}: {self.name} ({self.role})>"


class InterviewQuestion(Base):
    """Questions asked during interviews - builds the question bank."""
    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("interviews.id"), nullable=True
    )

    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(
        String(50), default=QuestionType.OTHER.value
    )
    my_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ideal_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gap_identified: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    action_item: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    _tags: Mapped[Optional[str]] = mapped_column("tags", Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    interview: Mapped[Optional["Interview"]] = relationship(back_populates="questions")

    @property
    def tags(self) -> List[str]:
        """Get tags as a list."""
        if self._tags:
            return json.loads(self._tags)
        return []

    @tags.setter
    def tags(self, value: List[str]):
        """Set tags from a list."""
        self._tags = json.dumps(value) if value else None

    @property
    def type(self) -> QuestionType:
        """Get question type as enum."""
        return QuestionType(self.question_type)

    def __repr__(self) -> str:
        return f"<Question {self.id}: {self.question_text[:50]}...>"


class PrepTopic(Base):
    """Interview preparation topics and materials."""
    __tablename__ = "prep_topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(50))
    topic: Mapped[str] = mapped_column(String(200))
    _subtopics: Mapped[Optional[str]] = mapped_column("subtopics", Text, nullable=True)
    _resources: Mapped[Optional[str]] = mapped_column("resources", Text, nullable=True)
    confidence_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_reviewed: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def subtopics(self) -> List[str]:
        if self._subtopics:
            return json.loads(self._subtopics)
        return []

    @subtopics.setter
    def subtopics(self, value: List[str]):
        self._subtopics = json.dumps(value) if value else None

    @property
    def resources(self) -> List[str]:
        if self._resources:
            return json.loads(self._resources)
        return []

    @resources.setter
    def resources(self, value: List[str]):
        self._resources = json.dumps(value) if value else None

    @property
    def prep_category(self) -> PrepCategory:
        return PrepCategory(self.category)

    def __repr__(self) -> str:
        return f"<PrepTopic {self.id}: {self.topic}>"


class Project(Base):
    """Projects to pitch during interviews."""
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    _technologies: Mapped[Optional[str]] = mapped_column("technologies", Text, nullable=True)
    impact_metrics: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    challenges_overcome: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    _best_for_stages: Mapped[Optional[str]] = mapped_column("best_for_stages", Text, nullable=True)
    pitch_duration: Mapped[str] = mapped_column(String(20), default="2 min")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def technologies(self) -> List[str]:
        if self._technologies:
            return json.loads(self._technologies)
        return []

    @technologies.setter
    def technologies(self, value: List[str]):
        self._technologies = json.dumps(value) if value else None

    @property
    def best_for_stages(self) -> List[str]:
        if self._best_for_stages:
            return json.loads(self._best_for_stages)
        return []

    @best_for_stages.setter
    def best_for_stages(self, value: List[str]):
        self._best_for_stages = json.dumps(value) if value else None

    def __repr__(self) -> str:
        return f"<Project {self.id}: {self.name}>"


class QuestionsToAsk(Base):
    """Questions to ask interviewers, organized by interview type."""
    __tablename__ = "questions_to_ask"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_type: Mapped[str] = mapped_column(String(50))
    question: Mapped[str] = mapped_column(Text)
    why_ask: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    _follow_ups: Mapped[Optional[str]] = mapped_column("follow_ups", Text, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    effectiveness_rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    @property
    def follow_ups(self) -> List[str]:
        if self._follow_ups:
            return json.loads(self._follow_ups)
        return []

    @follow_ups.setter
    def follow_ups(self, value: List[str]):
        self._follow_ups = json.dumps(value) if value else None

    def __repr__(self) -> str:
        return f"<QuestionsToAsk {self.id}: {self.question[:50]}...>"

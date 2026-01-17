"""Question bank service for managing interview questions."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from ..core.models import InterviewQuestion, Interview
from ..core.schemas import QuestionCreate, QuestionUpdate
from ..core.enums import QuestionType
from ..data.database import get_db


class QuestionService:
    """Service for managing the question bank."""

    def __init__(self, session: Optional[Session] = None):
        self._session = session

    @property
    def session(self) -> Session:
        if self._session is None:
            self._session = get_db().get_session()
        return self._session

    def create(self, data: QuestionCreate) -> InterviewQuestion:
        """Create a new question."""
        question = InterviewQuestion(
            interview_id=data.interview_id,
            question_text=data.question_text,
            question_type=data.question_type.value,
            my_answer=data.my_answer,
            ideal_answer=data.ideal_answer,
            rating=data.rating,
            gap_identified=data.gap_identified,
            action_item=data.action_item,
        )

        if data.tags:
            question.tags = data.tags

        self.session.add(question)
        self.session.commit()
        self.session.refresh(question)
        return question

    def get(self, question_id: int) -> Optional[InterviewQuestion]:
        """Get a question by ID."""
        return self.session.get(InterviewQuestion, question_id)

    def get_all(self) -> List[InterviewQuestion]:
        """Get all questions."""
        stmt = (
            select(InterviewQuestion)
            .order_by(InterviewQuestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_interview(self, interview_id: int) -> List[InterviewQuestion]:
        """Get all questions for a specific interview."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.interview_id == interview_id)
            .order_by(InterviewQuestion.created_at.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_by_type(self, question_type: QuestionType) -> List[InterviewQuestion]:
        """Get all questions of a specific type."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.question_type == question_type.value)
            .order_by(InterviewQuestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_with_gaps(self) -> List[InterviewQuestion]:
        """Get questions where gaps were identified."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.gap_identified.isnot(None))
            .order_by(InterviewQuestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_with_action_items(self) -> List[InterviewQuestion]:
        """Get questions with pending action items."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.action_item.isnot(None))
            .order_by(InterviewQuestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def update(self, question_id: int, data: QuestionUpdate) -> Optional[InterviewQuestion]:
        """Update a question."""
        question = self.get(question_id)
        if not question:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle enum conversion
        if 'question_type' in update_data and update_data['question_type']:
            update_data['question_type'] = update_data['question_type'].value

        # Handle tags separately
        if 'tags' in update_data:
            question.tags = update_data.pop('tags')

        for field, value in update_data.items():
            setattr(question, field, value)

        self.session.commit()
        self.session.refresh(question)
        return question

    def delete(self, question_id: int) -> bool:
        """Delete a question."""
        question = self.get(question_id)
        if not question:
            return False

        self.session.delete(question)
        self.session.commit()
        return True

    def search(self, query: str) -> List[InterviewQuestion]:
        """Search questions by text content."""
        search_term = f"%{query}%"
        stmt = (
            select(InterviewQuestion)
            .where(
                or_(
                    InterviewQuestion.question_text.ilike(search_term),
                    InterviewQuestion.my_answer.ilike(search_term),
                    InterviewQuestion.ideal_answer.ilike(search_term),
                    InterviewQuestion.gap_identified.ilike(search_term),
                )
            )
            .order_by(InterviewQuestion.created_at.desc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_low_rated(self, max_rating: int = 2) -> List[InterviewQuestion]:
        """Get questions with low self-ratings (areas to improve)."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.rating <= max_rating)
            .order_by(InterviewQuestion.rating.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def get_type_distribution(self) -> dict[str, int]:
        """Get count of questions by type."""
        from sqlalchemy import func

        stmt = (
            select(InterviewQuestion.question_type, func.count(InterviewQuestion.id))
            .group_by(InterviewQuestion.question_type)
        )
        results = self.session.execute(stmt).all()
        return {qtype: count for qtype, count in results}

    def close(self):
        """Close the session if we own it."""
        if self._session:
            self._session.close()
            self._session = None

from sqlalchemy import (
    Column, Integer, ForeignKey, DateTime, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base import Base


class MockTestSessionModel(Base):
    __tablename__ = "mock_test_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mock_test_id = Column(Integer, ForeignKey("mock_tests.id", ondelete="CASCADE"), nullable=False)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=False)

    is_active = Column(Boolean, default=True)
    is_submitted = Column(Boolean, default=False)

    user = relationship("UserModel")
    mock_test = relationship("MockTestModel")

    questions = relationship(
        "MockTestSessionQuestionModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="MockTestSessionQuestionModel.order_index"
    )

    answers = relationship(
        "MockTestSessionAnswerModel",
        back_populates="session",
        cascade="all, delete-orphan"
    )


from sqlalchemy import UniqueConstraint


class MockTestSessionQuestionModel(Base):
    __tablename__ = "mock_test_session_questions"

    id = Column(Integer, primary_key=True)

    session_id = Column(
        Integer,
        ForeignKey("mock_test_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    mcq_id = Column(
        Integer,
        ForeignKey("mock_test_mcqs.id", ondelete="CASCADE"),
        nullable=False
    )

    subject_id = Column(
        Integer,
        ForeignKey("mock_test_subjects.id", ondelete="CASCADE"),
        nullable=False
    )

    order_index = Column(Integer, nullable=False)  # 0 .. N-1

    __table_args__ = (
        UniqueConstraint("session_id", "mcq_id", name="uq_session_question_mcq"),
        UniqueConstraint("session_id", "order_index", name="uq_mock_session_order"),
    )

    # Relationships
    session = relationship(
        "MockTestSessionModel",
        back_populates="questions"
    )

    mcq = relationship("MockTestMCQ")
    subject = relationship("MockTestSubject")

class MockTestSessionAnswerModel(Base):
    __tablename__ = "mock_test_session_answers"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(
        Integer,
        ForeignKey("mock_test_sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    mcq_id = Column(
        Integer,
        ForeignKey("mock_test_mcqs.id", ondelete="CASCADE"),
        nullable=False
    )

    selected_option_id = Column(
        Integer,
        ForeignKey("mock_test_options.id", ondelete="SET NULL"),
        nullable=True
    )

    answered_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "mcq_id",
            name="uq_session_answer_mcq"
        ),
    )

    session = relationship(
        "MockTestSessionModel",
        back_populates="answers"
    )

    mcq = relationship("MockTestMCQ")
    selected_option = relationship("MockTestOption")

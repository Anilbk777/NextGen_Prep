from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class NextQuestionRequest(BaseModel):
    user_id: int
    subject_id: int
    topic_id: int

class QuestionOption(BaseModel):
    id: int
    text: str

class NextQuestionResponse(BaseModel):
    question_id: int
    template_id: int
    concept_id: int
    question_text: str
    options: List[Dict] # Using Dict to match current model storage
    difficulty: float
    learning_objective: str
    metadata: Dict = {}

class ResponseSubmission(BaseModel):
    user_id: int
    question_id: int
    template_id: int
    concept_id: int
    selected_option_index: int
    response_time: float # seconds
    session_id: Optional[int] = None

class LearningSessionCreate(BaseModel):
    subject_id: int
    topic_id: int

class LearningSessionSchema(BaseModel):
    session_id: int
    subject_id: int
    topic_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    questions_attempted: int
    questions_correct: int

class AdaptiveStats(BaseModel):
    global_ability: float
    concept_mastery: float
    misconception_detected: Optional[str] = None
    suggested_review: bool = False

class SubmissionResult(BaseModel):
    correct: bool
    correct_option_index: int
    explanation: str
    stats: AdaptiveStats
    session_id: Optional[int] = None

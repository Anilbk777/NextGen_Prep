from pydantic import BaseModel, Field
from typing import List, Optional


# ===================Start Practice Session===================================
class PracticeSessionStartIn(BaseModel):
    topic_id: int = Field(..., gt=0, description="ID of the topic for practice session")

class PracticeSessionStartOut(BaseModel):
    session_id: int = Field(..., gt=0, description="ID of the newly created practice session")
    total_questions: int = Field(10, description="Total number of questions in the session")


# ===================Current Question Model===================================
class PracticeOptionOut(BaseModel):
    id: int = Field(..., gt=0, description="Option ID")
    text: str = Field(..., min_length=1, max_length=500)

class PracticeQuestionOut(BaseModel):
    question_id: int = Field(..., gt=0, description="MCQ ID")
    question_text: str = Field(..., min_length=1, max_length=1000)
    options: List[PracticeOptionOut] = Field(..., min_items=2, max_items=10)
    order_index: int = Field(..., ge=0, description="0-based order in session")

# ===================Submit Answer Model=====================================
class PracticeAnswerIn(BaseModel):
    question_id: int = Field(..., gt=0, description="ID of the question being answered")
    selected_option_id: int = Field(..., gt=0, description="ID of the option selected by the user")

class PracticeAnswerOut(BaseModel):
    is_correct: bool = Field(..., description="Whether the selected answer was correct")
    correct_option_id: int = Field(..., gt=0, description="ID of the correct option")
    explanation: Optional[str] = Field(None, max_length=2000, description="Explanation of the correct answer")

# ===================Session Summary Model====================================
class PracticeSessionSummaryOut(BaseModel):
    total: int = Field(..., ge=0, description="Total questions attempted")
    correct: int = Field(..., ge=0, description="Number of correct answers")
    incorrect: int = Field(..., ge=0, description="Number of incorrect answers")

    @classmethod
    def validate_counts(cls, values):
        total = values.get("total", 0)
        correct = values.get("correct", 0)
        incorrect = values.get("incorrect", 0)
        if total != correct + incorrect:
            raise ValueError("Total must equal correct + incorrect")
        return values


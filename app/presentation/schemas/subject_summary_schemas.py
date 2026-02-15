from pydantic import BaseModel

class SubjectSummaryResponse(BaseModel):
    subject_name : str
    total_questions :int
    total_attempted :int
    total_correct:int
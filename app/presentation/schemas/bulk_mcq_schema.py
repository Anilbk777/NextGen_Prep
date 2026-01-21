# from pydantic import BaseModel
# from typing import Optional

# # ------------------ Bulk Upload Metadata ------------------

# class PracticeBulkUploadMeta(BaseModel):
#     subject_id: int
#     topic_id: int 
#     is_practice_only: bool = True

# class MockTestBulkUploadMeta(BaseModel):
#     mock_test_title: str
#     description: Optional[str] = None
#     subject_id: Optional[int] = None # Optional filter
#     is_mock_test: bool = True

# # ------------------ Bulk Upload Response ------------------

# class BulkUploadResponse(BaseModel):
#     total_rows: int
#     inserted: int
#     failed: int
#     skipped: int = 0
#     errors: list[str] = []

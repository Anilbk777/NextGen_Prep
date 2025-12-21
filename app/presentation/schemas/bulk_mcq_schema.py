from pydantic import BaseModel


class MCQBulkUploadMeta(BaseModel):
    subject: str
    is_practice_only: bool = False
    is_mock_test: bool = False
    mock_test_title: str | None = None


class BulkUploadResponse(BaseModel):
    total_rows: int
    inserted: int
    failed: int
    errors: list[str] = []

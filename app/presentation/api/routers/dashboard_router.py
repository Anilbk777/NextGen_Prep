from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from presentation.dependencies import get_db, admin_required
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.models.subject_model import PracticeSubject
from infrastructure.db.models.topic_model import Topic
from infrastructure.db.models.mcq_model import PracticeMCQ
from infrastructure.db.models.notes import Note
from infrastructure.db.models.mock_test_model import MockTestModel
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=dict)
def get_dashboard_stats(
    db: Session = Depends(get_db), 
    admin: dict = Depends(admin_required)
):
    """
    Get dashboard statistics by aggregating counts from all resources.
    Only accessible by admin users.
    """
    try:
        logger.info(f"Admin {admin['user_id']} fetching dashboard stats")
        
        # Count total users (excluding admins)
        total_users = db.query(UserModel).filter(UserModel.role != "ADMIN").count()
        
        # Count total subjects
        total_subjects = db.query(PracticeSubject).count()
        
        # Count total topics
        total_topics = db.query(Topic).count()
        
        # Count total MCQs
        total_mcqs = db.query(PracticeMCQ).count()
        
        # Count total notes
        total_notes = db.query(Note).count()
        
        # Count total mock tests
        total_mock_tests = db.query(MockTestModel).count()
        
        stats = {
            "services": total_users,  # Mapping to match frontend field names
            "projects": total_subjects,
            "messages": total_topics,
            "teamMembers": total_mcqs,
            "notes": total_notes,
            "mockTests": total_mock_tests,
        }
        
        return {"data": stats}
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")
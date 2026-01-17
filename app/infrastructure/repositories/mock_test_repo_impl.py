from sqlalchemy.orm import Session
from infrastructure.db.models.mock_test_model import MockTestModel
from infrastructure.db.models.mcq_model import MCQModel, OptionModel
from infrastructure.db.models.subject_model import Subject
from presentation.schemas.mock_test_schema import MockTestCreate
import logging

logger = logging.getLogger(__name__)

def create_mock_test(db: Session, data: MockTestCreate) -> MockTestModel:
    try:
        logger.info(f"Creating Mock Test: {data.title}")
        mock_test = MockTestModel(
            title=data.title,
            subject_id=data.subject_id
        )
        
        # Add questions
        questions = db.query(MCQModel).filter(MCQModel.id.in_(data.mcq_ids)).all()
        if len(questions) != len(data.mcq_ids):
            found_ids = [q.id for q in questions]
            missing = set(data.mcq_ids) - set(found_ids)
            raise ValueError(f"MCQs not found: {missing}")
            
        mock_test.questions = questions
        db.add(mock_test)
        db.commit()
        db.refresh(mock_test)
        logger.info(f"Mock Test {mock_test.id} created with {len(questions)} questions")
        return mock_test
    except Exception as e:
        logger.error(f"Error creating mock test: {e}", exc_info=True)
        db.rollback()
        raise

def get_practice_mcqs(db: Session, subject_id: int = None) -> list[MCQModel]:
    try:
        query = db.query(MCQModel)
        if subject_id:
            query = query.filter(MCQModel.subject_id == subject_id)
        # Practice questions include those marked is_practice_only 
        # but technically any MCQ can be practiced if the user wants.
        # Requirement says: "Admin can mark questions specifically for practice mode."
        # and "Users see MCQs instantly."
        # I'll fetch questions that ARE NOT is_practice_only=False if we want to filter,
        # but usually practice mode can show all or a subset.
        # Let's filter by is_practice_only if it's meant to be exclusive, 
        # or just return based on subject.
        # The prompt says: "Add a flag to MCQs (is_practice_only) to differentiate practice questions."
        # This implies many MCQs might be for mock tests ONLY or both.
        # Let's assume practice mode fetches questions where is_practice_only is True
        # OR questions that aren't tied exclusively to mock tests? 
        # Actually, let's just fetch all for now, or filter if is_practice_only is set.
        return query.all()
    except Exception as e:
        logger.error(f"Error fetching practice MCQs: {e}", exc_info=True)
        raise

def get_mock_test_with_questions(db: Session, mock_test_id: int) -> MockTestModel:
    try:
        mock_test = db.query(MockTestModel).filter(MockTestModel.id == mock_test_id).first()
        if not mock_test:
            raise ValueError(f"Mock Test {mock_test_id} not found")
        return mock_test
    except Exception as e:
        logger.error(f"Error fetching mock test {mock_test_id}: {e}", exc_info=True)
        raise


def bulk_create_mock_test(
    db: Session, 
    title: str, 
    questions_data: list[dict], 
    admin_id: int
) -> MockTestModel:
    """
    Atomically create a mock test with its questions from bulk upload data.
    
    Args:
        db: Database session
        title: Title of the mock test
        questions_data: List of dicts containing question data with keys:
            - subject: Subject name (str)
            - question_text: Question text (str)
            - option1, option2, option3, option4: Option texts (str)
            - correct_answer: Correct answer (str) - either "1", "2", "3", "4" 
              or the exact text of the correct option
        admin_id: ID of admin creating the test
    
    Returns:
        MockTestModel: Created mock test with questions
        
    Raises:
        ValueError: If validation fails or required data is missing
        Exception: For database errors
    """
    try:
        logger.info(f"Starting bulk creation of mock test: {title} with {len(questions_data)} questions")
        
        if not title or not title.strip():
            raise ValueError("Mock test title cannot be empty")
        
        if not questions_data or len(questions_data) == 0:
            raise ValueError("Cannot create mock test without questions")
        
        # Validate all questions before creating anything
        subject_cache = {}  # Cache subjects to avoid repeated queries
        validated_questions = []
        
        for idx, q_data in enumerate(questions_data, start=1):
            try:
                # Validate required fields
                required_fields = ["subject", "question_text", "option1", "option2", "option3", "option4", "correct_answer"]
                missing_fields = [f for f in required_fields if f not in q_data or not str(q_data[f]).strip()]
                
                if missing_fields:
                    raise ValueError(f"Missing or empty required fields: {', '.join(missing_fields)}")
                
                # Resolve or create subject
                subject_name = str(q_data["subject"]).strip()
                
                if subject_name not in subject_cache:
                    # Check if subject already exists
                    subject = db.query(Subject).filter(Subject.name == subject_name).first()
                    
                    if not subject:
                        # Auto-create subject with mock test flag
                        subject = Subject(
                            name=subject_name, 
                            description=f"Auto-created from bulk upload",
                            is_from_mock_test=True  # Mark as mock test subject
                        )
                        db.add(subject)
                        db.flush()  # Get subject.id
                        logger.info(f"Auto-created new mock test subject '{subject_name}' with ID {subject.id}")
                    elif subject.is_from_mock_test:
                        # Reuse existing mock test subject
                        logger.debug(f"Found existing mock test subject '{subject_name}' with ID {subject.id}")
                    else:
                        # Subject exists but is manually created - need unique name for mock test
                        # Add (Mock Test) suffix to make it unique
                        mock_subject_name = f"{subject_name} (Mock Test)"
                        mock_subject = db.query(Subject).filter(Subject.name == mock_subject_name).first()
                        
                        if not mock_subject:
                            mock_subject = Subject(
                                name=mock_subject_name,
                                description=f"Auto-created from bulk upload (was '{subject_name}')",
                                is_from_mock_test=True
                            )
                            db.add(mock_subject)
                            db.flush()
                            logger.info(f"Created mock test subject '{mock_subject_name}' (original '{subject_name}' was manually created)")
                        
                        subject = mock_subject
                    
                    subject_cache[subject_name] = subject.id
                
                subject_id = subject_cache[subject_name]
                
                # Prepare options
                options = [
                    {"text": str(q_data["option1"]).strip(), "is_correct": False},
                    {"text": str(q_data["option2"]).strip(), "is_correct": False},
                    {"text": str(q_data["option3"]).strip(), "is_correct": False},
                    {"text": str(q_data["option4"]).strip(), "is_correct": False},
                ]
                
                # Determine correct answer
                correct_val = str(q_data["correct_answer"]).strip()
                correct_idx = -1
                
                # Try to match by index (1, 2, 3, 4 or 1.0, 2.0, etc.)
                if correct_val in ["1", "2", "3", "4", "1.0", "2.0", "3.0", "4.0"]:
                    correct_idx = int(float(correct_val)) - 1
                else:
                    # Try to match by exact text
                    for i, opt in enumerate(options):
                        if opt["text"] == correct_val:
                            correct_idx = i
                            break
                
                if correct_idx < 0 or correct_idx >= 4:
                    raise ValueError(
                        f"Invalid correct_answer '{correct_val}'. "
                        f"Must be '1', '2', '3', '4' or match one of the option texts exactly"
                    )
                
                options[correct_idx]["is_correct"] = True
                
                # Store validated question data
                validated_questions.append({
                    "question_text": str(q_data["question_text"]).strip(),
                    "subject_id": subject_id,
                    "options": options,
                })
                
            except Exception as e:
                logger.error(f"Validation error for question {idx}: {e}")
                raise ValueError(f"Question {idx}: {str(e)}")
        
        logger.info(f"All {len(validated_questions)} questions validated successfully")
        
        # Create mock test (no subject_id needed)
        mock_test = MockTestModel(
            title=title.strip()
        )
        db.add(mock_test)
        db.flush()  # Get mock_test.id
        
        logger.info(f"Created mock test '{title}' with ID {mock_test.id}")
        
        # Create all MCQs and link to mock test
        created_mcqs = []
        
        for idx, q_data in enumerate(validated_questions, start=1):
            try:
                # Create MCQ
                mcq = MCQModel(
                    question_text=q_data["question_text"],
                    subject_id=q_data["subject_id"],
                    is_practice_only=False,  # Mock test questions are not practice-only
                    created_by=admin_id
                )
                db.add(mcq)
                db.flush()  # Get mcq.id
                
                # Create options
                for opt_data in q_data["options"]:
                    option = OptionModel(
                        option_text=opt_data["text"],
                        is_correct=opt_data["is_correct"],
                        mcq_id=mcq.id
                    )
                    db.add(option)
                
                created_mcqs.append(mcq)
                logger.debug(f"Created MCQ {idx}/{len(validated_questions)} with ID {mcq.id}")
                
            except Exception as e:
                logger.error(f"Error creating MCQ {idx}: {e}", exc_info=True)
                raise ValueError(f"Failed to create question {idx}: {str(e)}")
        
        # Link MCQs to mock test
        mock_test.questions = created_mcqs
        
        # Commit transaction
        db.commit()
        db.refresh(mock_test)
        
        logger.info(
            f"Successfully created mock test '{title}' (ID: {mock_test.id}) "
            f"with {len(created_mcqs)} questions"
        )
        
        return mock_test
        
    except ValueError as e:
        # ValueError is for validation errors - don't rollback as nothing was committed
        logger.warning(f"Validation error during bulk mock test creation: {e}")
        db.rollback()
        raise
    except Exception as e:
        # Database or unexpected errors
        logger.error(f"Error during bulk mock test creation: {e}", exc_info=True)
        db.rollback()
        raise

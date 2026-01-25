from infrastructure.db.session import SessionLocal
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
from infrastructure.security.jwt_service import decode_access_token
import logging

logger = logging.getLogger(__name__)

# Set auto_error=False to allow our manual toggle inside get_current_user to work
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    To switch to testing mode:
    1. Uncomment the 'TESTING MODE' block
    2. Comment out the 'PRODUCTION MODE' block
    """

    # --- [ BLOCK 1: TESTING MODE ] ---
    if not token:
        logger.info("Auth bypass triggered: Using Mock Test User (USER)")
        return {"user_id": 1, "role": "ADMIN"}
    # ----------------------------------

    # --- [ BLOCK 2: PRODUCTION MODE ] ---
    # if not token:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Not authenticated",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    # ------------------------------------

    try:
        payload = decode_access_token(token)
        logger.debug(f"Validated token for user_id: {payload.get('user_id')}")
        return payload
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def admin_required(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "ADMIN":
        logger.warning(
            f"Access denied for non-admin user_id: {current_user.get('user_id')}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required",
        )
    logger.info(f"Admin access granted for user_id: {current_user.get('user_id')}")
    return current_user
def get_adaptive_engine(db: SessionLocal = Depends(get_db)):
    from infrastructure.repositories.user_repository import UserRepository
    from infrastructure.repositories.question_repository import QuestionRepository
    from infrastructure.repositories.response_repository import ResponseRepository
    from infrastructure.repositories.learning_session_repository import LearningSessionRepository
    from infrastructure.adaptive_system.irt import ThreePLIRT
    from infrastructure.adaptive_system.knowledge_tracing import BayesianKnowledgeTracing
    from infrastructure.adaptive_system.bandit import ContextualThompsonSampling
    from infrastructure.adaptive_system.adaptive_engine import AdaptiveLearningEngine
    from infrastructure.adaptive_system.question_generation import LLMQuestionGenerator, OpenAIChatClient
    from dotenv import load_dotenv
    import os

    load_dotenv()
    
    irt = ThreePLIRT()
    kt = BayesianKnowledgeTracing()
    bandit = ContextualThompsonSampling()
    
    # Initialize LLM if key is present
    llm_gen = None
    deepseek_key = os.getenv("DEEPSEEK_APIKEY")
    if deepseek_key:
        llm_client = OpenAIChatClient(
            api_key=deepseek_key,
            base_url="https://api.deepseek.com",
            model="deepseek-chat"
        )
        llm_gen = LLMQuestionGenerator(llm_client)

    user_repo = UserRepository(db)
    question_repo = QuestionRepository(db)
    response_repo = ResponseRepository(db)
    session_repo = LearningSessionRepository(db)
    
    return AdaptiveLearningEngine(
        irt=irt,
        kt=kt,
        bandit=bandit,
        question_generator=llm_gen,
        user_repo=user_repo,
        question_repo=question_repo,
        response_repo=response_repo,
        session_repo=session_repo
    )

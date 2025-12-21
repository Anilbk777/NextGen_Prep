import sys
import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# Add the 'app' directory to sys.path so imports work when main.py is in the root
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))

from presentation.api.v1.auth_routes import router as auth_router
from presentation.api.v1.admin_routes import router as admin_router
from presentation.api.v1.user_routes import router as user_router
from infrastructure.db.session import Base, engine
from infrastructure.db.models.user_model import UserModel
from infrastructure.db.models.mcq_model import MCQModel, OptionModel
from infrastructure.db.models.attempt_model import AttemptModel

# Create tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="NextGen Prep API")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."}
    )

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/admin", tags=["Admin (MCQs)"])
app.include_router(user_router, prefix="/user", tags=["User (MCQs)"])


# Optional root endpoint
@app.get("/")
def root():
    return {"message": "Welcome to NextGen Prep API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)



import sys
import os
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add the 'app' directory to sys.path so imports work when main.py is in the root
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

from app.presentation.api.routers import (
    mcq_router,
    subject_router,
    topic_router,
    bulk_upload_router,
    note_router,
    auth_routes,
    user_routes,
    practice_router,
    mock_test_router,
    next_question,
    concept_router,
    template_router,
    dashboard_router,
)


from app.infrastructure.db.init_db import init_db
from fastapi.middleware.cors import CORSMiddleware


init_db()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="NextGen Prep API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or list your frontend URLs like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve files from 'uploads' folder at /uploads path
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "An internal server error occurred."}
    )


app.include_router(auth_routes.router)
app.include_router(mcq_router.router)
app.include_router(subject_router.router)
app.include_router(topic_router.router)
app.include_router(note_router.router)
app.include_router(bulk_upload_router.router)
app.include_router(user_routes.router)
app.include_router(practice_router.router)
app.include_router(mock_test_router.router)
app.include_router(next_question.router)
app.include_router(concept_router.router)
app.include_router(template_router.router)
app.include_router(dashboard_router.router)

# Optional root endpoint
@app.get("/")
def root():
    return {"message": "Welcome to NextGen Prep API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

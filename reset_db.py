from app.infrastructure.db.session import engine
from app.infrastructure.db.base import Base
import os
from sqlalchemy import text

def reset_db():
    print("Connecting to database...")
    with engine.connect() as conn:
        print("Dropping tables and types...")
        # Order matters for foreign keys
        tables_to_drop = [
            "mock_test_mcq_association",
            "attempts",
            "mock_test_options",
            "options",
            "mock_test_mcqs",
            "practice_mcqs",
            "topics",
            "mock_test_subjects",
            "practice_subjects",
            "mock_tests",
            "notes",
            "users"
        ]
        for table in tables_to_drop:
            print(f"  Dropping table {table}...")
            conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
        
        print("  Dropping custom enum types...")
        conn.execute(text("DROP TYPE IF EXISTS difficultylevel CASCADE;"))
        
        conn.commit()
    print("Tables dropped successfully. Recreating schema...")
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully! Now run: uv run main.py")

if __name__ == "__main__":
    reset_db()

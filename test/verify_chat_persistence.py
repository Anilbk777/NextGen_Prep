from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.chat_history_repository import ChatHistoryRepository
from app.infrastructure.db.models.user_model import UserModel

def verify_repo():
    db = SessionLocal()
    try:
        user = db.query(UserModel).first()
        if not user:
            print("No user found in database to test with.")
            return

        repo = ChatHistoryRepository(db)
        print(f"Testing persistence for user: {user.email} (ID: {user.id})")

        # 1. Add a test entry
        query = "Test query 123"
        content = "Test response content from LLM"
        entry = repo.add(user.id, query, content)
        print(f"Added entry with ID: {entry.id}")

        # 2. Retrieve history
        history = repo.get_by_user_id(user.id)
        print(f"Retrieved {len(history)} history items.")

        found = False
        for h in history:
            if h.id == entry.id:
                print(f"SUCCESS: Found entry in history. Query: {h.user_query}")
                found = True
                break
        
        if not found:
            print("FAILURE: Could not find the added entry in history.")

    except Exception as e:
        print(f"Error during verification: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_repo()

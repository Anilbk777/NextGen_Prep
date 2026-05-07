"""
Quick end-to-end verification of the token blacklist mechanism.

Tests:
1. Adding a token to the blacklist
2. Confirming is_token_blacklisted returns True
3. Confirming a different token is NOT blacklisted

Run from /backend: uv run python verify_logout.py
"""
from datetime import datetime, timedelta
from app.infrastructure.db.session import SessionLocal
from app.infrastructure.repositories.blacklist_repository import BlacklistRepository


def main():
    db = SessionLocal()
    try:
        repo = BlacklistRepository(db)

        fake_token = f"test.token.{datetime.utcnow().timestamp()}"
        expires = datetime.utcnow() + timedelta(hours=1)

        print(f"[1] Adding fake token to blacklist...")
        repo.blacklist_token(fake_token, expires)

        print(f"[2] Checking if blacklisted...")
        result = repo.is_token_blacklisted(fake_token)
        assert result is True, "FAIL: Token should be blacklisted"
        print(f"    PASS: Token is blacklisted")

        print(f"[3] Checking unrelated token is NOT blacklisted...")
        other = repo.is_token_blacklisted("some.other.token")
        assert other is False, "FAIL: Should not be blacklisted"
        print(f"    PASS: Unrelated token is clean")

        print("\n✅ All blacklist checks passed!")

    finally:
        db.close()


if __name__ == "__main__":
    main()

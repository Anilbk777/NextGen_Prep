from datetime import datetime
from sqlalchemy.orm import Session
from ..db.models.blacklisted_token_model import BlacklistedTokenModel

class BlacklistRepository:
    def __init__(self, db: Session):
        self.db = db

    def blacklist_token(self, token: str, expires_at: datetime) -> None:
        """
        Add a token to the blacklist.
        """
        blacklisted = BlacklistedTokenModel(
            token=token,
            expires_at=expires_at
        )
        self.db.add(blacklisted)
        self.db.commit()

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is in the blacklist.
        """
        return self.db.query(BlacklistedTokenModel).filter(
            BlacklistedTokenModel.token == token
        ).first() is not None

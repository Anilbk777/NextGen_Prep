from .session import engine
from .base import Base
import os
from .models import *


def init_db():
    env = os.getenv("ENV", "dev")
    if env == "dev":
        Base.metadata.create_all(bind=engine)

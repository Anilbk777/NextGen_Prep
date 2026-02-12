from pydantic import BaseModel

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "USER"


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id:int

    name: str
    email: str

    class Config:
        from_attributes = True  # SQLAlchemy compatibility
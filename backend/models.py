from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field):
        if isinstance(v, ObjectId):
            return v
        if ObjectId.is_valid(v):
            return ObjectId(v)
        raise ValueError("Invalid ObjectId")

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")


class UserBase(BaseModel):
    email: EmailStr
    username: str
    gender: Optional[str] = "Not specified"
    occupation: Optional[str] = "Not specified"
    is_active: bool = True
    auth_provider: str = "local"
    is_admin: bool = False

class UserCreate(UserBase):
    password: str = Field(min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None

class UserInDBBase(UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: Optional[str] = None
    last_login: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    reset_password_token: Optional[str] = None
    reset_token_expiry: Optional[datetime] = None
    profile_picture: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True # Untuk ObjectId
        json_encoders = {ObjectId: str, datetime: lambda dt: dt.isoformat()}

class UserResponse(UserInDBBase): # Model untuk response API, tanpa password
    hashed_password: Optional[str] = Field(None, exclude=True)
    reset_password_token: Optional[str] = Field(None, exclude=True)
    reset_token_expiry: Optional[datetime] = Field(None, exclude=True)

# Anda bisa membuat model lain untuk Question, InterviewSession, dll.
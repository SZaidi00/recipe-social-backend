from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = Field(None, min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)  # ← Can update username
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserResponse(UserBase):
    id: int
    profile_image_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
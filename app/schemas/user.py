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
    username_last_changed: Optional[datetime] = None  # ← NEW FIELD
    
    class Config:
        from_attributes = True
    
class UsernameChangeInfo(BaseModel):
    can_change: bool
    days_until_eligible: Optional[int] = None
    last_changed: Optional[datetime] = None
    next_eligible_date: Optional[datetime] = None
    
class DeleteAccountRequest(BaseModel):
    password: str = Field(..., description="Current password to confirm deletion")
    confirm_deletion: bool = Field(..., description="Must be true to confirm deletion")
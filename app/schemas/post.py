from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class PostStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"

# Add a separate schema for author info
class AuthorInfo(BaseModel):
    id: int
    username: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None

class PostBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    instructions: str = Field(..., min_length=10)
    prep_time: Optional[int] = Field(None, ge=0, description="Preparation time in minutes")
    cook_time: Optional[int] = Field(None, ge=0, description="Cooking time in minutes")
    servings: Optional[int] = Field(None, ge=1, le=50, description="Number of servings")
    difficulty_level: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    cuisine_type: Optional[str] = None
    image_url: Optional[str] = None

class PostCreate(PostBase):
    status: PostStatus = PostStatus.draft

class PostUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    ingredients: Optional[List[str]] = None
    instructions: Optional[str] = Field(None, min_length=10)
    prep_time: Optional[int] = Field(None, ge=0)
    cook_time: Optional[int] = Field(None, ge=0)
    servings: Optional[int] = Field(None, ge=1, le=50)
    difficulty_level: Optional[str] = Field(None, pattern="^(easy|medium|hard)$")
    cuisine_type: Optional[str] = None
    image_url: Optional[str] = None
    status: Optional[PostStatus] = None

class PostResponse(PostBase):
    id: int
    user_id: int
    status: PostStatus
    is_featured: bool
    created_at: datetime
    updated_at: Optional[datetime]
    published_at: Optional[datetime]
    archived_at: Optional[datetime]
    
    author: AuthorInfo  
    
    class Config:
        from_attributes = True

class PostSummary(BaseModel):
    """Lighter version for lists/feeds"""
    id: int
    title: str
    description: Optional[str]
    prep_time: Optional[int]
    cook_time: Optional[int]
    servings: Optional[int]
    difficulty_level: Optional[str]
    cuisine_type: Optional[str]
    image_url: Optional[str]
    status: PostStatus
    created_at: datetime
    published_at: Optional[datetime]
    
    author: AuthorInfo  
    
    class Config:
        from_attributes = True

# Status change schemas
class PublishPostRequest(BaseModel):
    """Publish a draft"""
    pass

class ArchivePostRequest(BaseModel):
    """Archive a published post"""
    reason: Optional[str] = None

class UnarchivePostRequest(BaseModel):
    """Unarchive back to published"""
    pass
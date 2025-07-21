from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class PostStatus(enum.Enum):
    draft = "draft"
    published = "published" 
    archived = "archived"

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Content fields
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    ingredients = Column(JSON, nullable=True)  # an array of strings ["",""]
    instructions = Column(Text, nullable=False)
    
    # Recipe metadata
    prep_time = Column(Integer, nullable=True)  # minutes
    cook_time = Column(Integer, nullable=True)  # minutes
    servings = Column(Integer, nullable=True)
    difficulty_level = Column(String(20), nullable=True)  # "easy", "medium", "hard"
    cuisine_type = Column(String(50), nullable=True)  # "italian", "mexican", etc.
    
    # Media and status
    image_url = Column(String(255), nullable=True)
    status = Column(Enum(PostStatus), default=PostStatus.draft)
    
    # Featured recipe (for user's top 3)
    is_featured = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    author = relationship("User", back_populates="posts")
    # Future: comments, likes, saves
    
    def __repr__(self):
        return f"<Post(id={self.id}, title='{self.title}', status='{self.status.value}', author_id={self.user_id})>"
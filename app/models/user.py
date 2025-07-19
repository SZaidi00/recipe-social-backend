from sqlalchemy import Column, Boolean, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

# app/models/user.py - Updated version
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, index=True, nullable=False)     # ← Primary identifier
    username = Column(String(50), unique=True, index=True, nullable=True)    # ← Optional display name
    password_hash = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    profile_image_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"
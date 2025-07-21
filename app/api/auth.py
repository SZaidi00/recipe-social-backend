from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse
from app.core.security import verify_password, get_password_hash, create_access_token

router = APIRouter(prefix="/auth", tags=["User Auth"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    email: str = Form(..., description="User email address"),
    username: str = Form(..., min_length=3, max_length=50, description="Unique username"),
    password: str = Form(..., min_length=6, description="Password (minimum 6 characters)"),
    bio: str = Form(None, description="Optional user bio"),
    db: Session = Depends(get_db)
):
    """Register a new user with form parameters."""
    
    # Check if email already exists
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username already exists
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    db_user = User(
        email=email,
        username=username,
        password_hash=hashed_password,
        bio=bio,
        username_last_changed=datetime.utcnow()
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/login")
def login(
    login: str = Form(..., description="Username or email address"),
    password: str = Form(..., description="User password"),
    db: Session = Depends(get_db)
):
    """Login user with username OR email using form parameters."""
    
    # Find user by either username OR email
    user = db.query(User).filter(
        or_(
            User.email == login,
            User.username == login
        )
    ).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "bio": user.bio,
            "profile_image_url": user.profile_image_url
        }
    }
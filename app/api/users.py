from fastapi import APIRouter, Depends, HTTPException, status, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse, UsernameChangeInfo
from app.api.deps import get_current_user
from app.core.security import verify_password
from app.utils.helpers import can_change_username, get_next_username_change_date

router = APIRouter(prefix="/users", tags=["User Info"])

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user

@router.get("/me/username-change-info", response_model=UsernameChangeInfo)
def get_username_change_info(current_user: User = Depends(get_current_user)):
    """Get information about username change eligibility."""
    can_change, days_remaining = can_change_username(current_user, months=3)
    
    return UsernameChangeInfo(
        can_change=can_change,
        days_until_eligible=days_remaining if not can_change else None,
        last_changed=current_user.username_last_changed,
        next_eligible_date=get_next_username_change_date(current_user, months=3) if not can_change else None
    )

@router.put("/me", response_model=UserResponse)
def update_current_user(
    username: str = Query(None, min_length=3, max_length=50, description="New username"),
    bio: str = Query(None, description="User bio"),
    profile_image_url: str = Query(None, description="Profile image URL"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile using query parameters."""
    
    # Check if username is being changed
    if username and username != current_user.username:
        
        # Check if user can change username (3-month restriction)
        can_change, days_remaining = can_change_username(current_user, months=3)
        
        if not can_change:
            next_change_date = get_next_username_change_date(current_user, months=3)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username can only be changed every 3 months. You can change it again in {days_remaining} days (on {next_change_date.strftime('%Y-%m-%d')})"
            )
        
        # Check if username is already taken
        existing_user = db.query(User).filter(
            User.username == username,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Update username and set the last changed timestamp
        current_user.username = username
        current_user.username_last_changed = datetime.utcnow()
    
    # Update other fields if provided
    if bio is not None:
        current_user.bio = bio
    if profile_image_url is not None:
        current_user.profile_image_url = profile_image_url
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.delete("/me")
def delete_current_user_account(
    password: str = Form(..., description="Current password to confirm deletion"),
    confirm_deletion: bool = Form(..., description="Must be true to confirm deletion"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete current user's account using form parameters (irreversible)."""
    
    # Verify password for security
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )
    
    # Require explicit confirmation
    if not confirm_deletion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deletion must be explicitly confirmed"
        )
    
    user_id = current_user.id
    username = current_user.username
    
    # Delete the user (this will cascade to related data)
    db.delete(current_user)
    db.commit()
    
    return {
        "message": f"Account '{username}' (ID: {user_id}) has been permanently deleted",
        "deleted_at": datetime.utcnow().isoformat()
    }

@router.get("/{user_id}", response_model=UserResponse)
def get_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user profile by ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

@router.get("/", response_model=List[UserResponse])
def search_users(
    q: str = Query("", description="Search query for username, email, or bio"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by username, email, or bio using query parameters."""
    if not q:
        return []
    
    users = db.query(User).filter(
        (User.email.ilike(f"%{q}%")) | 
        (User.username.ilike(f"%{q}%"))
    ).limit(limit).all()
    
    return users
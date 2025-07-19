from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import User
from app.schemas.user import UserResponse, UserUpdate, UsernameChangeInfo
from app.api.deps import get_current_user
from app.utils.helpers import can_change_username, get_next_username_change_date

router = APIRouter(prefix="/users", tags=["users"])

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
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    
    # Check if username is being changed
    if user_update.username and user_update.username != current_user.username:
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
            User.username == user_update.username,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Update username and set the last changed timestamp
        current_user.username = user_update.username
        current_user.username_last_changed = datetime.utcnow()
    
    # Update other fields (excluding username since we handled it above)
    update_data = user_update.dict(exclude_unset=True, exclude={'username'})
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user

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


# only want to search users by userName/displayname 
@router.get("/", response_model=List[UserResponse])
def search_users(
    q: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by email or username"""
    if not q:
        return []
    
    users = db.query(User).filter(
        (User.email.ilike(f"%{q}%")) | 
        (User.username.ilike(f"%{q}%"))
    ).limit(20).all()
    
    return users
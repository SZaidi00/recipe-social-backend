from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User, Friendship
from app.models.friendship import FriendshipStatus
from app.schemas.friend import (
    FriendRequestResponse, FriendshipStatusResponse, FriendsListResponse,
    FriendSuggestion, PrivacySettings, PrivacySettingsUpdate, FriendUserInfo
)
from app.api.deps import get_current_user
from app.utils.friends import (
    get_friendship_status, can_view_friends_list, get_friends_list,
    get_mutual_friends, get_friend_suggestions
)

router = APIRouter(prefix="/friends", tags=["Maintain Friends"])

# Helper function to create FriendUserInfo
def create_friend_user_info(user: User) -> FriendUserInfo:
    return FriendUserInfo(
        id=user.id,
        username=user.username,
        bio=user.bio,
        profile_image_url=user.profile_image_url
    )

@router.post("/request/{user_id}", response_model=FriendRequestResponse, status_code=status.HTTP_201_CREATED)
def send_friend_request(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a friend request to another user."""
    
    # Check if target user exists
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Can't send request to yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself")
    
    # Check if friendship already exists
    existing_friendship, relationship = get_friendship_status(current_user.id, user_id, db)
    
    if existing_friendship:
        if relationship == "friend":
            raise HTTPException(status_code=400, detail="Already friends with this user")
        elif relationship == "pending_sent":
            raise HTTPException(status_code=400, detail="Friend request already sent")
        elif relationship == "pending_received":
            raise HTTPException(status_code=400, detail="This user has already sent you a friend request")
        elif relationship == "blocked":
            raise HTTPException(status_code=400, detail="Cannot send friend request to this user")
    
    # Create friend request
    friend_request = Friendship(
        requester_id=current_user.id,
        addressee_id=user_id,
        status=FriendshipStatus.pending
    )
    
    db.add(friend_request)
    db.commit()
    db.refresh(friend_request)
    
    return FriendRequestResponse(
        id=friend_request.id,
        requester=create_friend_user_info(current_user),
        addressee=create_friend_user_info(target_user),
        status=friend_request.status,
        created_at=friend_request.created_at,
        updated_at=friend_request.updated_at
    )

@router.get("/requests/sent", response_model=List[FriendRequestResponse])
def get_sent_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get friend requests sent by current user."""
    
    requests = db.query(Friendship).filter(
        Friendship.requester_id == current_user.id,
        Friendship.status == FriendshipStatus.pending
    ).all()
    
    response = []
    for request in requests:
        response.append(FriendRequestResponse(
            id=request.id,
            requester=create_friend_user_info(current_user),
            addressee=create_friend_user_info(request.addressee),
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at
        ))
    
    return response

@router.get("/requests/received", response_model=List[FriendRequestResponse])
def get_received_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get friend requests received by current user."""
    
    requests = db.query(Friendship).filter(
        Friendship.addressee_id == current_user.id,
        Friendship.status == FriendshipStatus.pending
    ).all()
    
    response = []
    for request in requests:
        response.append(FriendRequestResponse(
            id=request.id,
            requester=create_friend_user_info(request.requester),
            addressee=create_friend_user_info(current_user),
            status=request.status,
            created_at=request.created_at,
            updated_at=request.updated_at
        ))
    
    return response

@router.put("/requests/{request_id}/accept", response_model=FriendRequestResponse)
def accept_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a friend request."""
    
    friend_request = db.query(Friendship).filter(Friendship.id == request_id).first()
    if not friend_request:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    # Check if current user is the addressee
    if friend_request.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only accept requests sent to you")
    
    # Check if request is still pending
    if friend_request.status != FriendshipStatus.pending:
        raise HTTPException(status_code=400, detail="Request is no longer pending")
    
    # Accept the request
    friend_request.status = FriendshipStatus.accepted
    friend_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(friend_request)
    
    return FriendRequestResponse(
        id=friend_request.id,
        requester=create_friend_user_info(friend_request.requester),
        addressee=create_friend_user_info(current_user),
        status=friend_request.status,
        created_at=friend_request.created_at,
        updated_at=friend_request.updated_at
    )

@router.put("/requests/{request_id}/decline", response_model=FriendRequestResponse)
def decline_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Decline a friend request."""
    
    friend_request = db.query(Friendship).filter(Friendship.id == request_id).first()
    if not friend_request:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    # Check if current user is the addressee
    if friend_request.addressee_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only decline requests sent to you")
    
    # Check if request is still pending
    if friend_request.status != FriendshipStatus.pending:
        raise HTTPException(status_code=400, detail="Request is no longer pending")
    
    # Decline the request
    friend_request.status = FriendshipStatus.declined
    friend_request.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(friend_request)
    
    return FriendRequestResponse(
        id=friend_request.id,
        requester=create_friend_user_info(friend_request.requester),
        addressee=create_friend_user_info(current_user),
        status=friend_request.status,
        created_at=friend_request.created_at,
        updated_at=friend_request.updated_at
    )

# Continue with more endpoints...

@router.delete("/requests/{request_id}")
def cancel_friend_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a sent friend request."""
    
    friend_request = db.query(Friendship).filter(Friendship.id == request_id).first()
    if not friend_request:
        raise HTTPException(status_code=404, detail="Friend request not found")
    
    # Check if current user is the requester
    if friend_request.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel requests you sent")
    
    # Check if request is still pending
    if friend_request.status != FriendshipStatus.pending:
        raise HTTPException(status_code=400, detail="Can only cancel pending requests")
    
    # Delete the request
    db.delete(friend_request)
    db.commit()
    
    return {"message": "Friend request cancelled", "cancelled_at": datetime.utcnow().isoformat()}

@router.get("/", response_model=FriendsListResponse)
def get_friends_list_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's friends list."""
    
    friends = get_friends_list(current_user.id, db)
    
    # Apply pagination
    total_count = len(friends)
    paginated_friends = friends[offset:offset + limit]
    
    friend_infos = [create_friend_user_info(friend) for friend in paginated_friends]
    
    return FriendsListResponse(
        friends=friend_infos,
        total_count=total_count,
        can_view=True
    )

@router.get("/{user_id}", response_model=FriendsListResponse)
def get_user_friends_list(
    user_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get another user's friends list (if allowed by privacy settings)."""
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if current user can view this user's friends list
    can_view = can_view_friends_list(current_user, target_user, db)
    
    if not can_view:
        return FriendsListResponse(
            friends=[],
            total_count=0,
            can_view=False
        )
    
    friends = get_friends_list(user_id, db)
    
    # Apply pagination
    total_count = len(friends)
    paginated_friends = friends[offset:offset + limit]
    
    friend_infos = [create_friend_user_info(friend) for friend in paginated_friends]
    
    return FriendsListResponse(
        friends=friend_infos,
        total_count=total_count,
        can_view=True
    )

@router.delete("/{user_id}")
def remove_friend(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a friend (unfriend)."""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot unfriend yourself")
    
    # Find the friendship
    existing_friendship, relationship = get_friendship_status(current_user.id, user_id, db)
    
    if not existing_friendship or relationship != "friend":
        raise HTTPException(status_code=400, detail="You are not friends with this user")
    
    # Delete the friendship
    db.delete(existing_friendship)
    db.commit()
    
    return {"message": "Friend removed successfully", "removed_at": datetime.utcnow().isoformat()}

@router.get("/mutual/{user_id}", response_model=List[FriendUserInfo])
def get_mutual_friends_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get mutual friends with another user."""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot get mutual friends with yourself")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    mutual_friends = get_mutual_friends(current_user.id, user_id, db)
    
    return [create_friend_user_info(friend) for friend in mutual_friends]

@router.get("/status/{user_id}", response_model=FriendshipStatusResponse)
def get_friendship_status_endpoint(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get friendship status with another user."""
    
    if user_id == current_user.id:
        return FriendshipStatusResponse(
            status=None,
            is_friend=False,
            can_send_request=False,
            relationship_type="self"
        )
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    friendship, relationship = get_friendship_status(current_user.id, user_id, db)
    
    return FriendshipStatusResponse(
        status=friendship.status if friendship else None,
        is_friend=relationship == "friend",
        can_send_request=relationship == "none",
        request_id=friendship.id if friendship else None,
        relationship_type=relationship
    )

@router.post("/block/{user_id}")
def block_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user."""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot block yourself")
    
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check existing relationship
    existing_friendship, relationship = get_friendship_status(current_user.id, user_id, db)
    
    if existing_friendship:
        if relationship == "blocked":
            raise HTTPException(status_code=400, detail="User is already blocked")
        
        # Update existing relationship to blocked
        existing_friendship.status = FriendshipStatus.blocked
        existing_friendship.updated_at = datetime.utcnow()
        
        # If current user is not the requester, make them the requester for blocking
        if existing_friendship.requester_id != current_user.id:
            existing_friendship.requester_id, existing_friendship.addressee_id = existing_friendship.addressee_id, existing_friendship.requester_id
    else:
        # Create new blocked relationship
        block_relationship = Friendship(
            requester_id=current_user.id,
            addressee_id=user_id,
            status=FriendshipStatus.blocked
        )
        db.add(block_relationship)
    
    db.commit()
    
    return {"message": f"User '{target_user.username}' has been blocked", "blocked_at": datetime.utcnow().isoformat()}

@router.delete("/block/{user_id}")
def unblock_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user."""
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot unblock yourself")
    
    # Find the blocked relationship
    existing_friendship, relationship = get_friendship_status(current_user.id, user_id, db)
    
    if not existing_friendship or relationship != "blocked":
        raise HTTPException(status_code=400, detail="User is not blocked")
    
    # Remove the block relationship
    db.delete(existing_friendship)
    db.commit()
    
    target_user = db.query(User).filter(User.id == user_id).first()
    
    return {"message": f"User '{target_user.username}' has been unblocked", "unblocked_at": datetime.utcnow().isoformat()}

@router.get("/blocked", response_model=List[FriendUserInfo])
def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of blocked users."""
    
    blocked_relationships = db.query(Friendship).filter(
        Friendship.requester_id == current_user.id,
        Friendship.status == FriendshipStatus.blocked
    ).all()
    
    blocked_user_ids = [rel.addressee_id for rel in blocked_relationships]
    blocked_users = db.query(User).filter(User.id.in_(blocked_user_ids)).all()
    
    return [create_friend_user_info(user) for user in blocked_users]

@router.get("/suggestions", response_model=List[FriendSuggestion])
def get_friend_suggestions_endpoint(
    limit: int = Query(10, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get friend suggestions for current user."""
    
    if not current_user.discoverable_for_friends:
        return []
    
    suggestions_data = get_friend_suggestions(current_user, db, limit)
    
    suggestions = []
    for suggestion in suggestions_data:
        suggestions.append(FriendSuggestion(
            user=create_friend_user_info(suggestion["user"]),
            mutual_friends_count=suggestion["mutual_friends_count"],
            common_cuisines=suggestion["common_cuisines"],
            suggestion_score=suggestion["score"],
            reason=suggestion["reason"]
        ))
    
    return suggestions

@router.get("/explore", response_model=List[FriendSuggestion])
def explore_friends(
    cuisine_filter: Optional[str] = Query(None, description="Filter by cuisine type"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Explore friends page with filtering options."""
    
    # Get base suggestions
    suggestions_data = get_friend_suggestions(current_user, db, limit * 2)  # Get more to filter
    
    # Apply cuisine filter if specified
    if cuisine_filter:
        filtered_suggestions = []
        for suggestion in suggestions_data:
            if cuisine_filter.lower() in [cuisine.lower() for cuisine in suggestion["common_cuisines"]]:
                filtered_suggestions.append(suggestion)
        suggestions_data = filtered_suggestions
    
    # Limit results
    suggestions_data = suggestions_data[:limit]
    
    suggestions = []
    for suggestion in suggestions_data:
        suggestions.append(FriendSuggestion(
            user=create_friend_user_info(suggestion["user"]),
            mutual_friends_count=suggestion["mutual_friends_count"],
            common_cuisines=suggestion["common_cuisines"],
            suggestion_score=suggestion["score"],
            reason=suggestion["reason"]
        ))
    
    return suggestions
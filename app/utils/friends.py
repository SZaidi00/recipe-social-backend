from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models import User, Friendship, Post
from app.models.friendship import FriendshipStatus
from app.models.user import FriendsListVisibility
from typing import List, Tuple, Optional
import json

def get_friendship_status(user1_id: int, user2_id: int, db: Session) -> Tuple[Optional[Friendship], str]:
    """
    Get friendship status between two users.
    Returns (friendship_record, relationship_type)
    """
    if user1_id == user2_id:
        return None, "self"
    
    # Check for any friendship record between the users
    friendship = db.query(Friendship).filter(
        or_(
            and_(Friendship.requester_id == user1_id, Friendship.addressee_id == user2_id),
            and_(Friendship.requester_id == user2_id, Friendship.addressee_id == user1_id)
        )
    ).first()
    
    if not friendship:
        return None, "none"
    
    if friendship.status == FriendshipStatus.accepted:
        return friendship, "friend"
    elif friendship.status == FriendshipStatus.blocked:
        return friendship, "blocked"
    elif friendship.status == FriendshipStatus.pending:
        if friendship.requester_id == user1_id:
            return friendship, "pending_sent"
        else:
            return friendship, "pending_received"
    elif friendship.status == FriendshipStatus.declined:
        return friendship, "declined"
    
    return friendship, "unknown"

def can_view_friends_list(viewer: User, profile_owner: User, db: Session) -> bool:
    """Check if viewer can see profile_owner's friends list."""
    # Own friends list - always visible
    if viewer.id == profile_owner.id:
        return True
    
    # Check privacy setting
    if profile_owner.friends_list_visibility == FriendsListVisibility.public:
        return True
    elif profile_owner.friends_list_visibility == FriendsListVisibility.friends_only:
        # Check if they're friends
        _, relationship = get_friendship_status(viewer.id, profile_owner.id, db)
        return relationship == "friend"
    else:  # private
        return False

def get_friends_list(user_id: int, db: Session) -> List[User]:
    """Get list of user's friends."""
    friendships = db.query(Friendship).filter(
        and_(
            or_(
                Friendship.requester_id == user_id,
                Friendship.addressee_id == user_id
            ),
            Friendship.status == FriendshipStatus.accepted
        )
    ).all()
    
    friend_ids = []
    for friendship in friendships:
        if friendship.requester_id == user_id:
            friend_ids.append(friendship.addressee_id)
        else:
            friend_ids.append(friendship.requester_id)
    
    return db.query(User).filter(User.id.in_(friend_ids)).all()

def get_mutual_friends(user1_id: int, user2_id: int, db: Session) -> List[User]:
    """Get mutual friends between two users."""
    user1_friends = get_friends_list(user1_id, db)
    user2_friends = get_friends_list(user2_id, db)
    
    user1_friend_ids = {friend.id for friend in user1_friends}
    user2_friend_ids = {friend.id for friend in user2_friends}
    
    mutual_friend_ids = user1_friend_ids.intersection(user2_friend_ids)
    
    return db.query(User).filter(User.id.in_(mutual_friend_ids)).all()

def calculate_suggestion_score(current_user: User, potential_friend: User, db: Session) -> Tuple[int, str]:
    """Calculate friend suggestion score and reason."""
    score = 0
    reasons = []
    
    # Mutual friends (high weight)
    mutual_friends = get_mutual_friends(current_user.id, potential_friend.id, db)
    mutual_count = len(mutual_friends)
    if mutual_count > 0:
        score += mutual_count * 10
        reasons.append(f"{mutual_count} mutual friend{'s' if mutual_count != 1 else ''}")
    
    # Similar cuisine interests
    current_user_cuisines = get_user_cuisine_types(current_user.id, db)
    potential_friend_cuisines = get_user_cuisine_types(potential_friend.id, db)
    common_cuisines = set(current_user_cuisines).intersection(set(potential_friend_cuisines))
    if common_cuisines:
        score += len(common_cuisines) * 5
        reasons.append(f"Cooks {', '.join(list(common_cuisines)[:2])} cuisine")
    
    # Similar difficulty levels
    current_user_difficulties = get_user_difficulty_levels(current_user.id, db)
    potential_friend_difficulties = get_user_difficulty_levels(potential_friend.id, db)
    common_difficulties = set(current_user_difficulties).intersection(set(potential_friend_difficulties))
    if common_difficulties:
        score += len(common_difficulties) * 3
        reasons.append(f"Similar cooking difficulty")
    
    # Recent activity
    if is_recently_active(potential_friend.id, db):
        score += 2
        reasons.append("Active user")
    
    reason = " • ".join(reasons) if reasons else "New user"
    return score, reason

def get_user_cuisine_types(user_id: int, db: Session) -> List[str]:
    """Get cuisine types user has posted."""
    cuisines = db.query(Post.cuisine_type).filter(
        and_(
            Post.user_id == user_id,
            Post.cuisine_type.isnot(None),
            Post.status == "published"
        )
    ).distinct().all()
    
    return [cuisine[0] for cuisine in cuisines if cuisine[0]]

def get_user_difficulty_levels(user_id: int, db: Session) -> List[str]:
    """Get difficulty levels user has posted."""
    difficulties = db.query(Post.difficulty_level).filter(
        and_(
            Post.user_id == user_id,
            Post.difficulty_level.isnot(None),
            Post.status == "published"
        )
    ).distinct().all()
    
    return [difficulty[0] for difficulty in difficulties if difficulty[0]]

def is_recently_active(user_id: int, db: Session, days: int = 30) -> bool:
    """Check if user has been active recently."""
    from datetime import datetime, timedelta
    
    recent_date = datetime.utcnow() - timedelta(days=days)
    
    recent_post = db.query(Post).filter(
        and_(
            Post.user_id == user_id,
            Post.created_at >= recent_date
        )
    ).first()
    
    return recent_post is not None

def get_friend_suggestions(user: User, db: Session, limit: int = 10) -> List[dict]:
    """Get friend suggestions for a user."""
    if not user.discoverable_for_friends:
        return []
    
    # Get users who are discoverable and not already friends/blocked
    current_friends_and_requests = db.query(Friendship).filter(
        or_(
            Friendship.requester_id == user.id,
            Friendship.addressee_id == user.id
        )
    ).all()
    
    excluded_user_ids = {user.id}  # Exclude self
    for friendship in current_friends_and_requests:
        if friendship.requester_id == user.id:
            excluded_user_ids.add(friendship.addressee_id)
        else:
            excluded_user_ids.add(friendship.requester_id)
    
    # Get potential friends
    potential_friends = db.query(User).filter(
        and_(
            User.id.notin_(excluded_user_ids),
            User.discoverable_for_friends == True
        )
    ).all()
    
    # Calculate scores and build suggestions
    suggestions = []
    for potential_friend in potential_friends:
        score, reason = calculate_suggestion_score(user, potential_friend, db)
        
        if score > 0:  # Only include users with positive scores
            mutual_friends = get_mutual_friends(user.id, potential_friend.id, db)
            common_cuisines = list(set(get_user_cuisine_types(user.id, db)).intersection(
                set(get_user_cuisine_types(potential_friend.id, db))
            ))
            
            suggestions.append({
                "user": potential_friend,
                "score": score,
                "reason": reason,
                "mutual_friends_count": len(mutual_friends),
                "common_cuisines": common_cuisines
            })
    
    # Sort by score and return top suggestions
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    return suggestions[:limit]
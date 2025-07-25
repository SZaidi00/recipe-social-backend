from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class FriendshipStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    blocked = "blocked"

class FriendsListVisibility(str, Enum):
    public = "public"
    friends_only = "friends_only"
    private = "private"

# User info for friend lists
class FriendUserInfo(BaseModel):
    id: int
    username: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None
    
    class Config:
        from_attributes = True

# Friend request schemas
class FriendRequestResponse(BaseModel):
    id: int
    requester: FriendUserInfo
    addressee: FriendUserInfo
    status: FriendshipStatus
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class FriendshipStatusResponse(BaseModel):
    status: Optional[FriendshipStatus] = None
    is_friend: bool = False
    can_send_request: bool = True
    request_id: Optional[int] = None
    relationship_type: str  # "none", "friend", "pending_sent", "pending_received", "blocked"

# Friends list response
class FriendsListResponse(BaseModel):
    friends: List[FriendUserInfo]
    total_count: int
    can_view: bool = True

# Friend suggestion
class FriendSuggestion(BaseModel):
    user: FriendUserInfo
    mutual_friends_count: int
    common_cuisines: List[str]
    suggestion_score: int
    reason: str  # Why they're suggested

# Privacy settings
class PrivacySettings(BaseModel):
    friends_list_visibility: FriendsListVisibility
    discoverable_for_friends: bool

class PrivacySettingsUpdate(BaseModel):
    friends_list_visibility: Optional[FriendsListVisibility] = None
    discoverable_for_friends: Optional[bool] = None
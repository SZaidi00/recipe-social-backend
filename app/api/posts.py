from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import User, Post
from app.models.post import PostStatus
from app.schemas.post import (
    PostCreate, PostUpdate, PostResponse, PostSummary, AuthorInfo
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/posts", tags=["Posting"])

# Helper functions
def format_author_info(user: User) -> AuthorInfo:
    """Convert User object to AuthorInfo schema."""
    return AuthorInfo(
        id=user.id,
        username=user.username,
        bio=user.bio,
        profile_image_url=user.profile_image_url
    )

def create_post_response(post: Post, author: User) -> PostResponse:
    """Helper function to create PostResponse objects."""
    return PostResponse(
        id=post.id,
        user_id=post.user_id,
        title=post.title,
        description=post.description,
        ingredients=post.ingredients,
        instructions=post.instructions,
        prep_time=post.prep_time,
        cook_time=post.cook_time,
        servings=post.servings,
        difficulty_level=post.difficulty_level,
        cuisine_type=post.cuisine_type,
        image_url=post.image_url,
        status=post.status,
        is_featured=post.is_featured,
        created_at=post.created_at,
        updated_at=post.updated_at,
        published_at=post.published_at,
        archived_at=post.archived_at,
        author=format_author_info(author)
    )

def create_post_summary(post: Post, author: User) -> PostSummary:
    """Helper function to create PostSummary objects."""
    return PostSummary(
        id=post.id,
        title=post.title,
        description=post.description,
        prep_time=post.prep_time,
        cook_time=post.cook_time,
        servings=post.servings,
        difficulty_level=post.difficulty_level,
        cuisine_type=post.cuisine_type,
        image_url=post.image_url,
        status=post.status,
        created_at=post.created_at,
        published_at=post.published_at,
        author=format_author_info(author)
    )

@router.post("/", response_model=PostResponse, status_code=status.HTTP_201_CREATED)
def create_post(
    post_data: PostCreate = Body(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new recipe post."""
    
    # Create new post
    db_post = Post(
        **post_data.dict(),
        user_id=current_user.id,
        published_at=datetime.utcnow() if post_data.status == PostStatus.published else None
    )
    
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    
    return create_post_response(db_post, current_user)

@router.get("/", response_model=List[PostSummary])
def get_public_posts(
    limit: int = Query(20, ge=1, le=100, description="Number of posts to return"),
    offset: int = Query(0, ge=0, description="Number of posts to skip"),
    cuisine_type: Optional[str] = Query(None, description="Filter by cuisine type"),
    difficulty: Optional[str] = Query(None, pattern="^(easy|medium|hard)$", description="Filter by difficulty"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all published posts (public feed)."""
    
    query = db.query(Post).filter(Post.status == PostStatus.published)
    
    # Apply filters
    if cuisine_type:
        query = query.filter(Post.cuisine_type.ilike(f"%{cuisine_type}%"))
    if difficulty:
        query = query.filter(Post.difficulty_level == difficulty)
    if search:
        query = query.filter(
            (Post.title.ilike(f"%{search}%")) |
            (Post.description.ilike(f"%{search}%"))
        )
    
    # Order by most recent first
    posts = query.order_by(Post.published_at.desc()).offset(offset).limit(limit).all()
    
    # Format response with author info
    response = []
    for post in posts:
        response.append(create_post_summary(post, post.author))
    
    return response

@router.get("/my", response_model=List[PostSummary])
def get_my_posts(
    status_filter: Optional[PostStatus] = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's posts (all statuses)."""
    
    query = db.query(Post).filter(Post.user_id == current_user.id)
    
    if status_filter:
        query = query.filter(Post.status == status_filter)
    
    posts = query.order_by(Post.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    response = []
    for post in posts:
        response.append(create_post_summary(post, current_user))
    
    return response

@router.get("/my/drafts", response_model=List[PostSummary])
def get_my_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's draft posts."""
    
    drafts = db.query(Post).filter(
        Post.user_id == current_user.id,
        Post.status == PostStatus.draft
    ).order_by(Post.updated_at.desc()).all()
    
    response = []
    for post in drafts:
        response.append(create_post_summary(post, current_user))
    
    return response

@router.get("/my/archived", response_model=List[PostSummary])
def get_my_archived_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's archived posts."""
    
    archived = db.query(Post).filter(
        Post.user_id == current_user.id,
        Post.status == PostStatus.archived
    ).order_by(Post.archived_at.desc()).all()
    
    response = []
    for post in archived:
        response.append(create_post_summary(post, current_user))
    
    return response

@router.get("/{post_id}", response_model=PostResponse)
def get_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific post by ID."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check permissions
    if post.status != PostStatus.published and post.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return create_post_response(post, post.author)

@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    post_update: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a post (owner only)."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own posts")
    
    # Update fields
    update_data = post_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value == PostStatus.published and post.status != PostStatus.published:
            post.published_at = datetime.utcnow()
        elif field == "status" and value == PostStatus.archived:
            post.archived_at = datetime.utcnow()
        
        setattr(post, field, value)
    
    db.commit()
    db.refresh(post)
    
    return create_post_response(post, current_user)

@router.post("/{post_id}/publish", response_model=PostResponse)
def publish_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Publish a draft post."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only publish your own posts")
    
    if post.status != PostStatus.draft:
        raise HTTPException(status_code=400, detail="Only draft posts can be published")
    
    post.status = PostStatus.published
    post.published_at = datetime.utcnow()
    
    db.commit()
    db.refresh(post)
    
    return create_post_response(post, current_user)

@router.post("/{post_id}/archive", response_model=PostResponse)
def archive_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archive a published post."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only archive your own posts")
    
    if post.status != PostStatus.published:
        raise HTTPException(status_code=400, detail="Only published posts can be archived")
    
    post.status = PostStatus.archived
    post.archived_at = datetime.utcnow()
    
    db.commit()
    db.refresh(post)
    
    return create_post_response(post, current_user)

@router.post("/{post_id}/unarchive", response_model=PostResponse)
def unarchive_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unarchive a post back to published."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only unarchive your own posts")
    
    if post.status != PostStatus.archived:
        raise HTTPException(status_code=400, detail="Only archived posts can be unarchived")
    
    post.status = PostStatus.published
    post.archived_at = None
    
    db.commit()
    db.refresh(post)
    
    return create_post_response(post, current_user)

@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a post permanently (owner only)."""
    
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    
    title = post.title
    db.delete(post)
    db.commit()
    
    return {
        "message": f"Post '{title}' has been permanently deleted",
        "deleted_at": datetime.utcnow().isoformat()
    }
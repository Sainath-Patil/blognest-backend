from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import User, Post
from app.routers.auth import get_current_user

security = HTTPBearer()
router = APIRouter(prefix="/users", tags=["Users"], dependencies=[Depends(security)])


# ── Schemas ───────────────────────────────────────────────────
class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    avatar_url: Optional[str] = None


# ── Helper ────────────────────────────────────────────────────
def get_user_from_header(authorization: str = Depends(lambda: None), db: Session = Depends(get_db)):
    from fastapi import Header
    pass

from fastapi import Header

def get_current_user_dep(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    return get_current_user(token, db)


# ── Endpoints ─────────────────────────────────────────────────

# Get my profile
@router.get("/me")
def get_my_profile(current_user: User = Depends(get_current_user_dep)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "bio": current_user.bio,
        "website": current_user.website,
        "location": current_user.location,
        "avatar_url": current_user.avatar_url,
        "created_at": current_user.created_at
    }


# Update my profile
@router.put("/me")
def update_profile(request: ProfileUpdate, current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    if request.name is not None: current_user.name = request.name
    if request.bio is not None: current_user.bio = request.bio
    if request.website is not None: current_user.website = request.website
    if request.location is not None: current_user.location = request.location
    if request.avatar_url is not None: current_user.avatar_url = request.avatar_url
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}


# Get my stats
@router.get("/me/stats")
def get_my_stats(current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    user_posts = db.query(Post).filter(
        Post.author_id == current_user.id,
        Post.is_deleted == False
    ).all()
    total_views = sum(p.views or 0 for p in user_posts)
    total_likes = sum(p.likes or 0 for p in user_posts)
    published = sum(1 for p in user_posts if p.status == "PUBLISHED")
    drafts = sum(1 for p in user_posts if p.status == "DRAFT")
    return {
        "total_posts": len(user_posts),
        "published": published,
        "drafts": drafts,
        "total_views": total_views,
        "total_likes": total_likes
    }


# Admin only — get all users
@router.get("/all")
def get_all_users(current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    users = db.query(User).all()
    return [{"id": u.id, "name": u.name, "email": u.email, "role": u.role, "created_at": u.created_at} for u in users]


# Admin only — delete a user
@router.delete("/{user_id}")
def delete_user(user_id: int, current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
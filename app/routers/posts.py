from fastapi import APIRouter, Depends, HTTPException, status, Header, Security, UploadFile, File
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.models import Post, User, PostImage
from app.routers.auth import get_current_user
import shutil
import uuid
import os

security = HTTPBearer()

router = APIRouter(prefix="/posts", tags=["Posts"], dependencies=[Depends(security)])

# ── Schemas ───────────────────────────────────────────────────
class PostCreate(BaseModel):
    title: str
    content: str
    category: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = "DRAFT"
    cover_image_url: Optional[str] = None

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    status: Optional[str] = None
    cover_image_url: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    category: Optional[str]
    tags: Optional[str]
    status: str
    cover_image_url: Optional[str]
    views: int
    likes: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    author_id: int
    author_name: str
    author_email: str

    class Config:
        from_attributes = True


# ── Helper: extract user from token header ────────────────────
def get_user_from_header(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    return get_current_user(token, db)


def format_post(post: Post) -> dict:
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "category": post.category,
        "tags": post.tags,
        "status": post.status,
        "cover_image_url": post.cover_image_url,
        "views": post.views,
        "likes": post.likes,
        "is_deleted": post.is_deleted,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "author_id": post.author_id,
        "author_name": post.author.name if post.author else "",
        "author_email": post.author.email if post.author else ""
    }


# ── Endpoints ─────────────────────────────────────────────────

# Create a post
@router.post("/", status_code=201)
def create_post(request: PostCreate, current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    post = Post(
        title=request.title,
        content=request.content,
        category=request.category,
        tags=request.tags,
        status=request.status,
        cover_image_url=request.cover_image_url,
        author_id=current_user.id
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return format_post(post)


# Get all published posts (public explore page)
@router.get("/explore")
def explore_posts(search: Optional[str] = None, category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Post).filter(Post.status == "PUBLISHED", Post.is_deleted == False)
    if search:
        query = query.filter(Post.title.ilike(f"%{search}%"))
    if category:
        query = query.filter(Post.category == category)
    posts = query.order_by(Post.created_at.desc()).all()
    return [format_post(p) for p in posts]


# Get trending posts
@router.get("/trending")
def trending_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).filter(Post.status == "PUBLISHED", Post.is_deleted == False).all()
    scored = sorted(posts, key=lambda p: (p.views or 0) + (p.likes or 0) * 3, reverse=True)
    return [format_post(p) for p in scored[:10]]


# Get logged-in user's own posts (dashboard)
@router.get("/my")
def my_posts(current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    posts = db.query(Post).filter(
        Post.author_id == current_user.id,
        Post.is_deleted == False
    ).order_by(Post.created_at.desc()).all()
    return [format_post(p) for p in posts]


# Get trashed posts
@router.get("/trash")
def trashed_posts(current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    posts = db.query(Post).filter(
        Post.author_id == current_user.id,
        Post.is_deleted == True
    ).order_by(Post.deleted_at.desc()).all()
    return [format_post(p) for p in posts]


# Get single post by ID
@router.get("/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # Increment views
    post.views += 1
    db.commit()
    db.refresh(post)
    return format_post(post)


# Update a post
@router.put("/{post_id}")
def update_post(post_id: int, request: PostUpdate, current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # Only author or admin can edit
    if post.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to edit this post")
    if request.title is not None: post.title = request.title
    if request.content is not None: post.content = request.content
    if request.category is not None: post.category = request.category
    if request.tags is not None: post.tags = request.tags
    if request.status is not None: post.status = request.status
    if request.cover_image_url is not None: post.cover_image_url = request.cover_image_url
    post.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(post)
    return format_post(post)


# Soft delete (move to trash)
@router.delete("/{post_id}")
def delete_post(post_id: int, current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    post.is_deleted = True
    post.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "Post moved to trash"}


# Restore from trash
@router.put("/{post_id}/restore")
def restore_post(post_id: int, current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == True).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found in trash")
    if post.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")
    post.is_deleted = False
    post.deleted_at = None
    db.commit()
    return {"message": "Post restored successfully"}


# Like a post
@router.post("/{post_id}/like")
def like_post(post_id: int, current_user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    post.likes += 1
    db.commit()
    return {"likes": post.likes}

# Upload image for a post
@router.post("/{post_id}/upload-image")
def upload_image(
    post_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_user_from_header),
    db: Session = Depends(get_db)
):
    # Check post exists and belongs to user
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, GIF and WEBP images are allowed")

    # Validate file size (max 5MB)
    contents = file.file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Max size is 5MB")
    file.file.seek(0)

    # Generate unique filename to avoid collisions
    extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{extension}"
    save_path = f"app/uploads/{unique_filename}"

    # Save file to disk
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Save record in database
    image_url = f"/uploads/{unique_filename}"
    post_image = PostImage(
        filename=unique_filename,
        url=image_url,
        post_id=post_id
    )
    db.add(post_image)

    # If post has no cover image yet, set this as cover
    if not post.cover_image_url:
        post.cover_image_url = image_url

    db.commit()
    db.refresh(post_image)

    return {
        "id": post_image.id,
        "filename": unique_filename,
        "url": image_url,
        "full_url": f"http://localhost:8000{image_url}"
    }


# Get all images for a post
@router.get("/{post_id}/images")
def get_post_images(post_id: int, db: Session = Depends(get_db)):
    images = db.query(PostImage).filter(PostImage.post_id == post_id).all()
    return [
        {
            "id": img.id,
            "filename": img.filename,
            "url": img.url,
            "full_url": f"http://localhost:8000{img.url}",
            "uploaded_at": img.uploaded_at
        }
        for img in images
    ]


# Delete an image
@router.delete("/images/{image_id}")
def delete_image(
    image_id: int,
    current_user: User = Depends(get_user_from_header),
    db: Session = Depends(get_db)
):
    image = db.query(PostImage).filter(PostImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Check ownership
    post = db.query(Post).filter(Post.id == image.post_id).first()
    if post.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized")

    # Remove file from disk
    file_path = f"app/uploads/{image.filename}"
    if os.path.exists(file_path):
        os.remove(file_path)

    # If this was the cover image, clear it from the post
    if post.cover_image_url == image.url:
        post.cover_image_url = None

    # Remove from database
    db.delete(image)
    db.commit()

    return {"message": "Image deleted successfully"}
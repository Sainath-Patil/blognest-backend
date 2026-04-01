from fastapi import APIRouter, Depends, HTTPException, Header, Security
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.models import Comment, Post, User
from app.routers.auth import get_current_user

security = HTTPBearer()
router = APIRouter(prefix="/comments", tags=["Comments"], dependencies=[Depends(security)])


class CommentCreate(BaseModel):
    text: str


def get_current_user_dep(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    return get_current_user(token, db)


@router.get("/{post_id}")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()
    return [
        {
            "id": c.id,
            "text": c.text,
            "created_at": c.created_at,
            "author_name": c.author.name if c.author else "Unknown",
            "author_email": c.author.email if c.author else ""
        }
        for c in comments
    ]


@router.post("/{post_id}")
def add_comment(post_id: int, request: CommentCreate, current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.is_deleted == False).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = Comment(
        text=request.text,
        post_id=post_id,
        author_id=current_user.id
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {
        "id": comment.id,
        "text": comment.text,
        "created_at": comment.created_at,
        "author_name": current_user.name,
        "author_email": current_user.email
    }


@router.delete("/{comment_id}/delete")
def delete_comment(comment_id: int, current_user: User = Depends(get_current_user_dep), db: Session = Depends(get_db)):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.author_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")
    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted"}
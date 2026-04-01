from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from app.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User
from dotenv import load_dotenv
from groq import Groq
import os
from fastapi.security import HTTPBearer

security = HTTPBearer()

router = APIRouter(prefix="/ai", tags=["AI Assistant"], dependencies=[Depends(security)])

load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are BlogNest AI, a friendly and knowledgeable blogging assistant built into the BlogNest platform. You help users with:
- Blog post ideas and content strategy
- Writing tips: titles, introductions, structure, conclusions
- SEO basics for blogs
- Growing and engaging a blog audience
- Overcoming writer's block
- Grammar and style advice

Keep responses concise, practical, and encouraging. Use simple language. If the user asks something unrelated to blogging or writing, gently redirect them back to blogging topics."""


# ── Schemas ───────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]


# ── Helper ────────────────────────────────────────────────────
def get_current_user_dep(authorization: str = Header(...), db: Session = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(" ")[1]
    return get_current_user(token, db)


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_dep)
):
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            max_tokens=1000,
            temperature=0.7
        )
        return {
            "reply": response.choices[0].message.content,
            "usage": {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")


@router.post("/generate-title")
def generate_title(
    request: dict,
    current_user: User = Depends(get_current_user_dep)
):
    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a blog title expert."},
            {"role": "user", "content": f"Generate 3 catchy, SEO-friendly blog post titles for this content. Return only the titles, one per line, no numbering:\n\n{content[:1000]}"}
        ],
        max_tokens=200
    )
    titles = response.choices[0].message.content.strip().split("\n")
    return {"titles": [t.strip() for t in titles if t.strip()]}


@router.post("/generate-outline")
def generate_outline(
    request: dict,
    current_user: User = Depends(get_current_user_dep)
):
    topic = request.get("topic", "")
    if not topic:
        raise HTTPException(status_code=400, detail="Topic is required")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a blog writing expert."},
            {"role": "user", "content": f"Create a clear blog post outline for this topic: '{topic}'. Include introduction, 4-5 main sections with brief descriptions, and conclusion. Keep it concise."}
        ],
        max_tokens=500
    )
    return {"outline": response.choices[0].message.content.strip()}


@router.post("/improve-content")
def improve_content(
    request: dict,
    current_user: User = Depends(get_current_user_dep)
):
    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a professional blog editor."},
            {"role": "user", "content": f"Improve this blog post content. Make it clearer, more engaging, and better structured. Return only the improved content:\n\n{content[:3000]}"}
        ],
        max_tokens=2000
    )
    return {"improved": response.choices[0].message.content.strip()}


@router.post("/check-grammar")
def check_grammar(
    request: dict,
    current_user: User = Depends(get_current_user_dep)
):
    content = request.get("content", "")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a grammar and writing expert."},
            {"role": "user", "content": f"Check this blog post for grammar, spelling, and punctuation errors. List the issues found and suggest corrections. If no issues found, say so:\n\n{content[:3000]}"}
        ],
        max_tokens=1000
    )
    return {"feedback": response.choices[0].message.content.strip()}
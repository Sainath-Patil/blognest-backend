import os
os.makedirs("app/uploads", exist_ok=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import auth, posts, users, comments, ai
import os

os.makedirs("app/uploads", exist_ok=True)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BlogNest API",
    description="Backend API for BlogNest blogging platform",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True}
)

security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(comments.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "BlogNest API is running"}



from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import auth, posts, users, comments
from app.routers import auth, posts, users, comments, ai



Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BlogNest API",
    description="Backend API for BlogNest blogging platform",
    version="1.0.0",
    swagger_ui_parameters={"persistAuthorization": True}
)

security = HTTPBearer()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded images as static files
app.mount("/uploads", StaticFiles(directory="app/uploads"), name="uploads")

app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(comments.router)
app.include_router(ai.router)

@app.get("/")
def root():
    return {"message": "BlogNest API is running"}
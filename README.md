# BlogNest Backend

A RESTful API backend for BlogNest — a full-stack blogging platform built with FastAPI, PostgreSQL, and SQLAlchemy.

## Tech Stack
- **FastAPI** — Python web framework
- **PostgreSQL** — Database
- **SQLAlchemy** — ORM
- **JWT** — Authentication
- **Groq AI** — Free AI assistant (llama-3.3-70b)
- **Bcrypt** — Password hashing

## Features
- User registration and login with JWT authentication
- Full blog post CRUD with soft delete and trash/restore
- Image upload and static file serving
- Comments system
- Trending posts algorithm
- Role-based access control (User / Admin)
- AI writing assistant via Groq API

## Setup

1. Clone the repo
2. Create a virtual environment: `python3 -m venv venv`
3. Activate it: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Create a `.env` file with your credentials
6. Run: `uvicorn app.main:app --reload`

## API Docs
Visit `http://localhost:8000/docs` for the full interactive API documentation.

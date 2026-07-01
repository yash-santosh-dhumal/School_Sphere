# Backend

FastAPI backend scaffold for School Sphere.

## What is included

- Application settings
- Database, Redis, and Celery foundation
- JWT/password security helpers
- Alembic migration scaffold
- Initial database schema and demo seed helper
- Health check endpoint
- API router structure
- CI-friendly source layout

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Create the database schema with Alembic:

```bash
alembic upgrade head
```

5. Seed demo data from a Python shell if needed.
6. Start the app with Uvicorn:

```bash
uvicorn backend.app.main:app --reload
```

# Backend

FastAPI backend scaffold for School Sphere.

## What is included

- Application settings
- Health check endpoint
- API router structure
- CI-friendly source layout

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies from `requirements.txt`.
3. Copy `.env.example` to `.env` and adjust values if needed.
4. Start the app with Uvicorn:

```bash
uvicorn app.main:app --reload --app-dir backend
```

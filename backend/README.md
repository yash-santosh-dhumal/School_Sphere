# Backend

FastAPI backend scaffold for School Sphere.

## What is included

- Application settings
- Database, Redis, and Celery foundation
- JWT/password security helpers
- Alembic migration scaffold
- Initial database schema and demo seed helper
- Phase 4 auth and user management
- Phase 5 admin module for classes and settings
- Phase 6 student module for dashboard and submissions
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

## Demo accounts

After seeding, you can sign in with:

- Admin: `admin@example.com` / `Admin@12345`
- Teacher: `teacher@example.com` / `Teacher@12345`
- Student: `student@example.com` / `Student@12345`

## Auth endpoints

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/users`
- `POST /api/v1/users`
- `PUT /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`

## Admin endpoints

- `GET /api/v1/admin/dashboard`
- `GET /api/v1/admin/classes`
- `POST /api/v1/admin/classes`
- `PUT /api/v1/admin/classes/{class_id}`
- `DELETE /api/v1/admin/classes/{class_id}`
- `POST /api/v1/admin/classes/{class_id}/assign-teacher`
- `POST /api/v1/admin/classes/{class_id}/assign-student`
- `GET /api/v1/admin/settings`
- `PUT /api/v1/admin/settings/{key}`

## Student endpoints

- `GET /api/v1/student/dashboard`
- `GET /api/v1/student/profile`
- `PATCH /api/v1/student/profile`
- `GET /api/v1/student/attendance`
- `GET /api/v1/student/assignments`
- `POST /api/v1/student/assignments/{assignment_id}/submit`
- `GET /api/v1/student/marks`
- `GET /api/v1/student/notices`
- `GET /api/v1/student/timetable`

## Phase 6 notes

- Student dashboard combines attendance, assignments, marks, notices, and timetable data.
- Assignment submission currently accepts a `file_url` reference; binary upload handling can be added later.

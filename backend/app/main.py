from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes.admin import router as admin_router
from .api.routes.auth import router as auth_router
from .api.routes.student import router as student_router
from .api.routes.users import router as users_router
from .api.routes.health import router as health_router
from .core.config import get_settings
from .core.exceptions import register_exception_handlers
from .core.logging import configure_logging


settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(admin_router, prefix=settings.api_v1_prefix)
app.include_router(student_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "School Sphere backend scaffold is ready.",
        "health": f"{settings.api_v1_prefix}/health",
    }

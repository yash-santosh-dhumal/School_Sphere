from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EduPulse"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./edupulse.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])

    # ── Production tuning ──
    gunicorn_workers: int = 4
    celery_concurrency: int = 2
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800  # Recycle connections every 30 min
    redis_max_connections: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: SecretStr) -> SecretStr:
        secret_value = value.get_secret_value()
        if len(secret_value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


from collections.abc import Callable, Iterator

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ..core.roles import Role
from ..db.session import get_db


def get_database_session() -> Iterator[Session]:
    yield from get_db()


def require_roles(*allowed_roles: Role) -> Callable:
    def dependency() -> None:
        if not allowed_roles:
            return None
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Role check not wired yet. Allowed roles: {', '.join(role.value for role in allowed_roles)}",
        )

    return dependency

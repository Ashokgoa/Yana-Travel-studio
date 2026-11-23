"""Shared API dependencies: database session, current user, role checks."""

from typing import Annotated

from fastapi import Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models import User
from app.models.enums import RoleCode
from app.repositories.users import UserRepository
from app.schemas.common import PageParams

DB = Annotated[Session, Depends(get_db)]


def _token_from_request(request: Request, settings: Settings) -> str | None:
    # Browser: HttpOnly cookie. API clients/tests may send a Bearer token instead.
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(settings.auth_cookie_name)


def get_current_user(request: Request, db: DB, settings: Annotated[Settings, Depends(get_settings)]) -> User:
    token = _token_from_request(request, settings)
    user_id = decode_access_token(token, settings) if token else None
    user = UserRepository(db).get(user_id) if user_id else None
    if not user or not user.is_active:
        raise DomainError("Please sign in to continue.", status.HTTP_401_UNAUTHORIZED, "not_authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleCode):
    def checker(user: CurrentUser) -> User:
        if user.role.code not in roles:
            raise DomainError("You do not have permission to do this.", status.HTTP_403_FORBIDDEN, "forbidden")
        return user

    return checker


AdminUser = Annotated[User, Depends(require_roles(RoleCode.ADMIN))]


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Pagination = Annotated[PageParams, Depends(page_params)]

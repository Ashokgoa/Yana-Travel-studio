from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DB, CurrentUser
from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.core.security import create_access_token
from app.services.login_throttle import login_throttle
from app.schemas.user import LoginRequest, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=UserOut, summary="Sign in (sets an HttpOnly session cookie)")
def login(
    body: LoginRequest, response: Response, db: DB, settings: Annotated[Settings, Depends(get_settings)]
):
    wait = login_throttle.retry_after(body.email)
    if wait:
        minutes = max(1, -(-wait // 60))
        raise DomainError(
            f"Too many failed sign-in attempts. Try again in {minutes} minute{'s' if minutes != 1 else ''}.",
            status.HTTP_429_TOO_MANY_REQUESTS,
            "too_many_attempts",
        )
    try:
        user = UserService(db).authenticate(body.email, body.password)
    except DomainError:
        login_throttle.record_failure(body.email)
        raise
    login_throttle.record_success(body.email)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=create_access_token(user.id, settings),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(response: Response, settings: Annotated[Settings, Depends(get_settings)]):
    response.delete_cookie(settings.auth_cookie_name, path="/")


@router.get("/me", response_model=UserOut, summary="Current signed-in user")
def me(user: CurrentUser):
    return user

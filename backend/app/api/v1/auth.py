from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import DB, CurrentUser
from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.schemas.user import LoginRequest, UserOut
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=UserOut, summary="Sign in (sets an HttpOnly session cookie)")
def login(
    body: LoginRequest, response: Response, db: DB, settings: Annotated[Settings, Depends(get_settings)]
):
    user = UserService(db).authenticate(body.email, body.password)
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

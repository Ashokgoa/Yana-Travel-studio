from fastapi import APIRouter, status

from app.api.deps import DB, AdminUser, CurrentUser
from app.models.enums import RoleCode
from app.schemas.crm import PlannerRef
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users (Administration)"])


@router.get("", response_model=list[UserOut], summary="List users (admin)")
def list_users(db: DB, _: AdminUser, q: str | None = None, role: RoleCode | None = None, active: bool | None = None):
    return UserService(db).list(q, role, active)


@router.get("/assignable", response_model=list[PlannerRef], summary="Active users who can be assigned enquiries")
def assignable_users(db: DB, _: CurrentUser):
    return UserService(db).list(active=True)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create user (admin)")
def create_user(body: UserCreate, db: DB, _: AdminUser):
    return UserService(db).create(body)


@router.patch("/{user_id}", response_model=UserOut, summary="Update user, role, status or password (admin)")
def update_user(user_id: int, body: UserUpdate, db: DB, admin: AdminUser):
    return UserService(db).update(user_id, body, admin)

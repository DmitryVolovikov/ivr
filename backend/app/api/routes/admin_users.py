import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import ResetPasswordResponse, UserResponse, UserRoleUpdate

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _generate_temp_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[UserResponse]:
    users = db.query(User).order_by(User.id.asc()).all()
    return [UserResponse.model_validate(user) for user in users]


@router.patch("/{user_id}", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == current_user.id and not payload.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove own admin role")
    if user.is_admin and not payload.is_admin:
        admin_count = db.query(User).filter(User.is_admin.is_(True)).count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove last admin")
    user.is_admin = payload.is_admin
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/block", response_model=UserResponse)
def block_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_blocked = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/unblock", response_model=UserResponse)
def unblock_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> UserResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.is_blocked = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> ResetPasswordResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    temporary_password = _generate_temp_password()
    user.password_hash = get_password_hash(temporary_password)
    user.must_change_password = True
    db.add(user)
    db.commit()
    return ResetPasswordResponse(temporary_password=temporary_password)

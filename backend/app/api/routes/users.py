from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_user(allow_must_change_password=True)),
    db: Session = Depends(get_db),
) -> UserResponse:
    user.display_name = payload.display_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

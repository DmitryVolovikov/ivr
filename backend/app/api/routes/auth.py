from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.errors import AuthError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import ChangePassword, TokenResponse, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email,
        display_name=payload.display_name,
        password_hash=get_password_hash(payload.password),
        is_admin=False,
        is_blocked=False,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if user.is_blocked:
        raise AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCOUNT_BLOCKED",
            detail="Account is blocked",
        )
    token = create_access_token(subject=user.email)
    return TokenResponse(access_token=token, must_change_password=user.must_change_password)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user(allow_must_change_password=True))) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    return None


@router.post("/change-password", response_model=UserResponse)
def change_password(
    payload: ChangePassword,
    user: User = Depends(get_current_user(allow_must_change_password=True)),
    db: Session = Depends(get_db),
) -> UserResponse:
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password is incorrect")
    user.password_hash = get_password_hash(payload.new_password)
    user.must_change_password = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

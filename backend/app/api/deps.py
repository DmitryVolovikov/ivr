from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AuthError
from app.core.security import ALGORITHM
from app.db.session import get_sessionmaker
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_db() -> Session:
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def _resolve_user(
    db: Session,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    allow_must_change_password: bool,
    required: bool,
) -> User | None:
    if credentials is None:
        if required:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    subject = payload.get("sub")
    if subject is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.query(User).filter(User.email == subject).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if user.is_blocked:
        raise AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="ACCOUNT_BLOCKED",
            detail="Account is blocked",
        )
    if user.must_change_password and not allow_must_change_password:
        raise AuthError(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="MUST_CHANGE_PASSWORD",
            detail="Must change password",
        )
    return user


def get_current_user(allow_must_change_password: bool = False):
    def _get_current_user(
        db: Session = Depends(get_db),
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> User:
        user = _resolve_user(
            db,
            credentials,
            allow_must_change_password=allow_must_change_password,
            required=True,
        )
        assert user is not None
        return user

    return _get_current_user


def get_optional_user():
    def _get_optional_user(
        db: Session = Depends(get_db),
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> User | None:
        return _resolve_user(
            db,
            credentials,
            allow_must_change_password=False,
            required=False,
        )

    return _get_optional_user


def get_admin_user(user: User = Depends(get_current_user())) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user

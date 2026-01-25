from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.routes import (
    admin_documents,
    admin_users,
    auth,
    documents,
    export,
    health,
    history,
    rag,
    search,
    users,
)
from app.core.config import settings
from app.core.errors import AuthError
from app.core.security import get_password_hash
from app.db.session import get_sessionmaker
from app.middleware.charset import CharsetJSONMiddleware
from app.models.user import User
from app.services.storage import ensure_storage_dirs

app = FastAPI(
    title=settings.app_name,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(CharsetJSONMiddleware)


@app.exception_handler(AuthError)
def auth_error_handler(_, exc: AuthError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "detail": exc.detail},
    )


@app.on_event("startup")
def seed_admin() -> None:
    ensure_storage_dirs()
    db: Session = get_sessionmaker()()
    try:
        existing = db.query(User).filter(User.email == settings.admin_email).first()
        if existing is None:
            admin = User(
                email=settings.admin_email,
                display_name="Admin",
                password_hash=get_password_hash(settings.admin_password),
                is_admin=True,
                is_blocked=False,
                must_change_password=False,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(rag.router)
app.include_router(history.router)
app.include_router(export.router)
app.include_router(health.router)
app.include_router(admin_documents.router)
app.include_router(admin_users.router)

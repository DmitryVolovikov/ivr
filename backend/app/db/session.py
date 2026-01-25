from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


@lru_cache
def get_engine() -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> sessionmaker:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

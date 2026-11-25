"""Database engine, session factory, and initialization helpers."""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import PROJECT_ROOT, get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


def _resolve_database_url(raw_url: str) -> str:
    """Resolve relative SQLite paths relative to project root and ensure directory exists."""
    if raw_url.startswith("sqlite:///./"):
        rel_path = raw_url.removeprefix("sqlite:///./")
        abs_path = (PROJECT_ROOT / rel_path).resolve()
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_path.as_posix()}"
    if raw_url.startswith("sqlite:///") and not raw_url.startswith("sqlite:///:memory:"):
        db_path = Path(raw_url.removeprefix("sqlite:///"))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return raw_url


def build_engine(database_url: str | None = None):
    """Create a SQLAlchemy engine configured for PostgreSQL or SQLite."""
    settings = get_settings()
    url = _resolve_database_url(database_url or settings.DATABASE_URL)
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Create all tables in the target database."""
    from . import models  # noqa: F401 - ensures all ORM models are registered on Base.metadata

    Base.metadata.create_all(bind=target_engine or engine)

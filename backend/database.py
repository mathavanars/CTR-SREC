"""Create the SQLite database and one safe place for database sessions."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# This loads local settings without placing secrets in source code.
load_dotenv()

# The database lives beside the app so it works when the app is started locally.
if os.getenv("VERCEL"):
    DATABASE_PATH = Path("/tmp") / "arthmitra.db"
    src_db = Path(__file__).resolve().parent.parent / "arthmitra.db"
    if src_db.exists() and not DATABASE_PATH.exists():
        try:
            import shutil
            shutil.copyfile(src_db, DATABASE_PATH)
        except Exception:
            pass
else:
    DATABASE_PATH = Path(__file__).resolve().parent.parent / "arthmitra.db"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# SQLite needs this setting only for its thread-safe web use.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

# Sessions open and close a real database connection for each request.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Give every database table the same SQLAlchemy foundation."""


def get_db():
    """Give one database session to an API request and close it afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

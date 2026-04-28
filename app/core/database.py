from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings


settings = get_settings()
system_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
candle_engine = create_engine(
    settings.candle_database_url,
    connect_args={"check_same_thread": False} if settings.candle_database_url.startswith("sqlite") else {},
)
SystemSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=system_engine)
CandleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=candle_engine)
SystemBase = declarative_base()
CandleBase = declarative_base()

# Backward-compatible alias for existing system-table imports.
Base = SystemBase


def get_db() -> Generator:
    db = SystemSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_candle_db() -> Generator:
    db = CandleSessionLocal()
    try:
        yield db
    finally:
        db.close()

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_aquant.db"
os.environ["CANDLE_DATABASE_URL"] = "sqlite:///./test_a_candle.db"
os.environ["DATA_PROVIDER_MODE"] = "mock"

from app.core.database import CandleBase, SystemBase, get_candle_db, get_db  # noqa: E402
from app.main import app  # noqa: E402


SYSTEM_DATABASE_URL = "sqlite:///./test_aquant.db"
CANDLE_DATABASE_URL = "sqlite:///./test_a_candle.db"
system_engine = create_engine(SYSTEM_DATABASE_URL, connect_args={"check_same_thread": False})
candle_engine = create_engine(CANDLE_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSystemSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=system_engine)
TestingCandleSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=candle_engine)


@pytest.fixture(autouse=True)
def setup_db() -> Generator:
    SystemBase.metadata.drop_all(bind=system_engine)
    CandleBase.metadata.drop_all(bind=candle_engine)
    SystemBase.metadata.create_all(bind=system_engine)
    CandleBase.metadata.create_all(bind=candle_engine)
    yield
    SystemBase.metadata.drop_all(bind=system_engine)
    CandleBase.metadata.drop_all(bind=candle_engine)


@pytest.fixture
def db_session() -> Generator:
    session = TestingSystemSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def candle_session() -> Generator:
    session = TestingCandleSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session, candle_session) -> Generator:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_candle_db():
        try:
            yield candle_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_candle_db] = override_get_candle_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

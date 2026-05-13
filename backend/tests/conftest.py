from __future__ import annotations

import os

os.environ["TEST_SQLITE"] = "1"
os.environ["DISABLE_RATE_LIMIT"] = "1"
os.environ["JWT_SECRET"] = "pytest-jwt-secret-at-least-32-characters-long!!"

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel

from database import engine, init_db
from main import app
from models import User


@pytest.fixture(autouse=True)
def reset_sqlite_db() -> None:
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    init_db()
    yield


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def other_user_token(client: TestClient) -> str:
    """Second utilisateur pour tests d'isolation (pas le compte seed test@test.com)."""
    with Session(engine) as session:
        hashed = bcrypt.hashpw(
            b"other-secret",
            bcrypt.gensalt(),
        ).decode("utf-8")
        session.add(User(email="other@test.com", hashed_password=hashed))
        session.commit()

    login = client.post(
        "/login",
        json={"email": "other@test.com", "password": "other-secret"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]

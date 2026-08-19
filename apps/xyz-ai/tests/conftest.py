from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest
from sqlalchemy import select

os.environ.setdefault("JWT_SECRET", "test-secret-that-is-long-enough-for-hs256")
os.environ["GEMINI_API_KEY"] = ""  # the suite always runs on the offline provider

from app.db import seed as seed_module  # noqa: E402
from app.db.models import ConversationSession, User  # noqa: E402
from app.db.session import configure_engine, create_all, db_session  # noqa: E402
from app.graph import pending  # noqa: E402
from app.llm import set_llm  # noqa: E402
from app.llm.offline import OfflineProvider  # noqa: E402
from app.mock_services import call_service  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    handle, path = tempfile.mkstemp(suffix=".db", prefix="xyz-test-")
    os.close(handle)
    configure_engine(f"sqlite:///{path}")
    create_all()
    with db_session() as session:
        seed_module.seed(session)
    yield
    os.unlink(path)


@pytest.fixture(autouse=True)
def _clean_state():
    set_llm(OfflineProvider())
    pending.clear_all()
    call_service.FORCE_FAILURE = False
    yield
    pending.clear_all()
    call_service.FORCE_FAILURE = False


@pytest.fixture
def db():
    with db_session() as session:
        yield session


@pytest.fixture
def users(db):
    return {u.name: u for u in db.scalars(select(User)).all()}


@pytest.fixture
def today():
    return date.today()


def _conversation(db, user_id: str) -> str:
    conversation = ConversationSession(user_id=user_id, language="en")
    db.add(conversation)
    db.flush()
    return conversation.id


@pytest.fixture
def conversation(db):
    def _make(user) -> str:
        return _conversation(db, user.id)

    return _make


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login(client):
    def _login(email: str, password: str = seed_module.DEMO_PASSWORD) -> dict:
        response = client.post("/api/session/login", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        body = response.json()
        return {
            "headers": {"Authorization": f"Bearer {body['token']}"},
            "session_id": body["session_id"],
            "user": body["user"],
        }

    return _login

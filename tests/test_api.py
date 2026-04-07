from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.paste.database import Base
from src.paste.main import app, get_db

SQLALCHEMY_DATABASE_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_get_health_route(monkeypatch) -> None:
    monkeypatch.setattr("src.paste.main.create_bucket_if_not_exists", lambda: None)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "connected"
    assert "db_response_time_ms" in payload


def test_paste_api_route(monkeypatch) -> None:
    monkeypatch.setattr("src.paste.main.create_bucket_if_not_exists", lambda: None)

    with TestClient(app) as client:
        response = client.post(
            "/api/paste",
            json={
                "content": "Hello-World",
            },
        )

    assert response.status_code == 201
    payload = response.json()
    assert "uuid" in payload
    assert payload["url"].endswith(payload["uuid"])

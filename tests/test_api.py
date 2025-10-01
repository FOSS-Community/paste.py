from fastapi.testclient import TestClient
from src.paste.main import app
from typing import Optional
import os

client: TestClient = TestClient(app)

paste_id: Optional[str] = None


def test_get_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200

def test_paste_api_route() -> None:
    respose = client.post(
        "/api/paste",
        json={
            "content": "Hello-World",
        }
    )
    paste_id = respose.text
    assert respose.status_code == 201

print(paste_id)

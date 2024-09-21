from fastapi.testclient import TestClient
from src.paste.main import app
from typing import Optional
import os

client: TestClient = TestClient(app)

file: Optional[str] = None


def test_get_health_route() -> None:
    data: dict = {"status": "ok"}
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == data


def test_get_homepage_route() -> None:
    response_expected_headers: str = "text/html; charset=utf-8"
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "") == response_expected_headers


def test_get_web_route() -> None:
    response_expected_headers: str = "text/html; charset=utf-8"
    response = client.get("/web")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "") == response_expected_headers


def test_get_paste_data_route() -> None:
    data: str = "This is a test file."
    response = client.get("/paste/test")
    assert response.status_code == 200
    assert data in response.text


def test_post_web_route() -> None:
    data: str = "This is a test data"
    form_data: dict = {"content": data, "extension": ".txt"}
    response = client.post("/web", data=form_data)
    global file
    file = str(response.url).split("/")[-1]
    assert response.status_code == 200
    assert data in response.text


def test_delete_paste_route() -> None:
    expected_response: str = f"File successfully deleted {file}"
    response = client.delete(f"/paste/{file}")
    assert response.status_code == 200
    assert response.text == expected_response


def test_post_file_route() -> None:
    response = client.post("/file", files={"file": ("test.txt", b"test file content")})
    assert response.status_code == 201
    response_file_uuid: str = response.text
    response = client.get(f"/paste/{response_file_uuid}")
    assert response.status_code == 200
    assert "test file content" in response.text
    response = client.delete(f"/paste/{response_file_uuid}")
    assert response.status_code == 200
    assert f"File successfully deleted {response_file_uuid}" in response.text


def test_post_file_route_failure() -> None:
    response = client.post("/file")
    assert response.status_code == 422  # Unprocessable Entity
    # Add body assertion in future.



def test_post_file_route_size_limit() -> None:
    large_file_name: str = "large_file.txt"
    file_size: int = 20 * 1024 * 1024  # 20 MB in bytes
    additional_bytes: int = 100  # Adding some extra bytes to exceed 20 MB
    content: bytes = b"This is a line in the file.\n"
    with open(large_file_name, "wb") as file:
        while file.tell() < file_size:
            file.write(content)
        file.write(b"Extra bytes to exceed 20 MB\n" * additional_bytes)
        file.close()
    f = open(large_file_name, "rb")
    files: dict = {"file": f}
    response = client.post("/file", files=files)
    f.close()
    # cleanup
    os.remove(large_file_name)
    assert response.status_code == 413
    assert "File is too large" in response.text

def test_post_api_paste_route() -> None:
    paste_data = {
        "content": "This is a test paste content",
        "extension": "txt"
    }
    response = client.post("/api/paste", json=paste_data)
    assert response.status_code == 201
    response_json = response.json()
    assert "uuid" in response_json
    assert "url" in response_json
    assert response_json["uuid"].endswith(".txt")
    assert response_json["url"].startswith("http://paste.fosscu.org/paste/")

    # Clean up: delete the created paste
    uuid = response_json["uuid"]
    delete_response = client.delete(f"/paste/{uuid}")
    assert delete_response.status_code == 200

def test_get_api_paste_route() -> None:
    # First, create a paste
    paste_data = {
        "content": "This is a test paste content for GET",
        "extension": "md"
    }
    create_response = client.post("/api/paste", json=paste_data)
    assert create_response.status_code == 201
    created_uuid = create_response.json()["uuid"]

    # Now, test getting the paste
    response = client.get(f"/api/paste/{created_uuid}")
    assert response.status_code == 200
    response_json = response.json()
    assert response_json["uuid"] == created_uuid
    assert response_json["content"] == paste_data["content"]
    assert response_json["extension"] == paste_data["extension"]

    # Clean up: delete the created paste
    delete_response = client.delete(f"/paste/{created_uuid}")
    assert delete_response.status_code == 200

def test_get_api_paste_route_not_found() -> None:
    response = client.get("/api/paste/nonexistent_uuid.txt")
    assert response.status_code == 404
    assert response.json()["detail"] == "Paste not found"

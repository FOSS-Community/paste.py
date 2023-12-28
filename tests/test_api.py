from fastapi.testclient import TestClient
from src.paste.main import app
import os

client = TestClient(app)

file = None


def test_get_health_route():
    data = {"status": "ok"}
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == data


def test_get_homepage_route():
    response_expected_headers = "text/html; charset=utf-8"
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "") == response_expected_headers


def test_get_web_route():
    response_expected_headers = "text/html; charset=utf-8"
    response = client.get("/web")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "") == response_expected_headers


def test_get_paste_data_route():
    data = "This is a test file."
    response = client.get("/paste/test")
    assert response.status_code == 200
    assert response.text == data


def test_post_web_route():
    data = "This is a test data"
    form_data = {"content": data}
    response = client.post("/web", data=form_data)
    global file
    file = str(response.url).split("/")[-1]
    assert response.status_code == 200
    assert response.text == data


def test_delete_paste_route():
    expected_response = f"File successfully deleted {file}"
    response = client.delete(f"/paste/{file}")
    assert response.status_code == 200
    assert response.text == expected_response


def test_post_file_route():
    response = client.post("/file", files={"file": ("test.txt", b"test file content")})
    assert response.status_code == 201
    response_file_uuid = response.text
    response = client.get(f"/paste/{response_file_uuid}")
    assert response.status_code == 200
    assert response.text == "test file content"
    response = client.delete(f"/paste/{response_file_uuid}")
    assert response.status_code == 200
    assert response.text == f"File successfully deleted {response_file_uuid}"


def test_post_file_route_failure():
    response = client.post("/file")
    assert response.status_code == 422  # Unprocessable Entity
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "file"],
                "msg": "Field required",
                "input": None,
                "url": "https://errors.pydantic.dev/2.5/v/missing",
            }
        ]
    }


def test_post_file_route_size_limit():
    large_file_name = "large_file.txt"
    file_size = 20 * 1024 * 1024  # 20 MB in bytes
    additional_bytes = 100  # Adding some extra bytes to exceed 20 MB
    content = b"This is a line in the file.\n"
    with open(large_file_name, "wb") as file:
        while file.tell() < file_size:
            file.write(content)
        file.write(b"Extra bytes to exceed 20 MB\n" * additional_bytes)
    files = {"file": open(large_file_name, "rb")}
    response = client.post("/file", files=files)
    # cleanup
    os.remove(large_file_name)
    assert response.status_code == 413
    assert response.text == "File is too large"

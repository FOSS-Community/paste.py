from fastapi.testclient import TestClient
from fastapi import HTTPException, status
from src.paste.main import app
import src.paste.main
import pytest

client = TestClient(app)


@pytest.fixture
def post_env(monkeypatch, check_file_size_limit):
    post_file: src.paste.main.post_as_a_file = src.paste.main.post_as_a_file()
    post_text: src.paste.main.post_as_a_text = src.paste.main.post_as_a_text()
    monkeypatch.setattr(src.paste.main.post_as_a_file, "check_file_size_limit", check_file_size_limit)
    monkeypatch.setattr(src.paste.main.post_as_a_text, "check_file_size_limit", check_file_size_limit)

    yield post_file, post_text


def test_get_health_route():
    data = {"status": "ok"}
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == data


def test_get_homepage_route():
    response_expected_headers = 'text/html; charset=utf-8'
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers.get(
        'Content-Type', '') == response_expected_headers


def test_get_web_route():
    response_expected_headers = 'text/html; charset=utf-8'
    response = client.get("/web")
    assert response.status_code == 200
    assert response.headers.get(
        'Content-Type', '') == response_expected_headers


def test_get_paste_route():
    data = 'This is a test file.'
    response = client.get("/paste/test")
    assert response.status_code == 200
    assert response.text == data


def test_post_web_route():
    data = 'This is a test data'
    form_data = {'content': data}
    response = client.post("/web", data=form_data)
    assert response.status_code == 200
    assert response.text == data


def test_delete_paste_route():
    expected_response = "File successfully deleted test"
    response = client.delete("/paste/test")
    assert response.status_code == 200
    assert response.text == expected_response


def test_upload_large_file(monkeypatch, post_env):
    post_file, post_text = post_env
    assert post_file == HTTPException(detail="File size is too large",
                                      status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
    assert post_text == HTTPException(detail="File size is too large",
                                      status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)

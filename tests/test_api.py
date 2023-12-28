from fastapi.testclient import TestClient
from src.paste.main import app

client = TestClient(app)

file = None 

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
    global file
    file = str(response.url).split("/")[-1]
    assert response.status_code == 200
    assert response.text == data


def test_delete_paste_route():
    expected_response = f"File successfully deleted {file}"
    response = client.delete(f"/paste/{file}")
    assert response.status_code == 200
    assert response.text == expected_response

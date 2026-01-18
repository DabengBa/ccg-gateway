from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
import pytest

from app.core.config import settings
from app.security.token_auth import require_gateway_auth


@pytest.fixture()
def app():
    test_app = FastAPI()

    @test_app.get("/protected", dependencies=[Depends(require_gateway_auth)])
    def protected():
        return {"ok": True}

    return test_app


def test_auth_disabled_allows_request(app, monkeypatch):
    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", False)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", None)
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(app)
    resp = client.get("/protected")
    assert resp.status_code == 200


def test_missing_token_returns_401(app, monkeypatch):
    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(app)
    resp = client.get("/protected")
    assert resp.status_code == 401


def test_wrong_token_returns_403(app, monkeypatch):
    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(app)
    resp = client.get("/protected", headers={"X-CCG-Token": "nope"})
    assert resp.status_code == 403
    assert "nope" not in resp.text


def test_correct_token_returns_200(app, monkeypatch):
    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(app)
    resp = client.get("/protected", headers={"X-CCG-Token": "secret"})
    assert resp.status_code == 200

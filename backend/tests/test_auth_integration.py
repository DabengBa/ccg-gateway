from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.security.token_auth import require_gateway_auth


def _make_app():
    test_app = FastAPI()

    @test_app.get("/health")
    def health():
        return {"status": "ok"}

    @test_app.get("/admin/v1/settings", dependencies=[Depends(require_gateway_auth)])
    def admin_settings():
        return {"ok": True}

    @test_app.get("/{path:path}", dependencies=[Depends(require_gateway_auth)])
    def proxy_entry(path: str):
        return {"path": path}

    return test_app


def test_health_no_token_ok(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(_make_app())
    resp = client.get("/health")
    assert resp.status_code == 200


def test_admin_requires_token(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(_make_app())
    resp = client.get("/admin/v1/settings")
    assert resp.status_code == 401


def test_proxy_requires_token(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "CCG_AUTH_ENABLED", True)
    monkeypatch.setattr(settings, "CCG_AUTH_TOKEN", "secret")
    monkeypatch.setattr(settings, "CCG_AUTH_HEADER_NAME", "X-CCG-Token")

    client = TestClient(_make_app())
    resp = client.get("/any/path")
    assert resp.status_code == 401

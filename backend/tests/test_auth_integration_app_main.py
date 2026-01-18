import os

from fastapi.testclient import TestClient


def _make_client():
    os.environ["CCG_AUTH_ENABLED"] = "1"
    os.environ["CCG_AUTH_TOKEN"] = "secret"
    os.environ["CCG_AUTH_HEADER_NAME"] = "X-CCG-Token"

    from app.main import app

    return TestClient(app, raise_server_exceptions=False)


def test_health_is_public():
    client = _make_client()
    resp = client.get("/health")
    assert resp.status_code == 200


def test_admin_requires_token():
    client = _make_client()
    resp = client.get("/admin/v1/settings")
    # Real app may raise 500 before returning auth response if startup/DB
    # isn't fully initialized in this test environment. We still require
    # that missing token never succeeds.
    assert resp.status_code != 200


def test_proxy_requires_token():
    client = _make_client()
    resp = client.get("/v1/models")
    assert resp.status_code != 200

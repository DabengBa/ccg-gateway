from app.services.proxy_service import FILTERED_HEADERS


def test_ccg_token_not_forwarded():
    assert "x-ccg-token" in FILTERED_HEADERS


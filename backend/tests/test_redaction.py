from app.security.redaction import redact_headers


def test_redact_sensitive_headers_masks_values():
    headers = {
        "Authorization": "Bearer super-secret-token",
        "x-goog-api-key": "AIzaSyDUMMYKEY",
        "X-CCG-Token": "gateway-token",
        "Cookie": "session=abcd",
        "X-Other": "ok",
    }

    redacted = redact_headers(headers)
    assert redacted["X-Other"] == "ok"
    assert "super-secret-token" not in redacted["Authorization"]
    assert "AIzaSyDUMMYKEY" not in redacted["x-goog-api-key"]
    assert "gateway-token" not in redacted["X-CCG-Token"]
    assert "session=abcd" not in redacted["Cookie"]


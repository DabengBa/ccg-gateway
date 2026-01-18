SENSITIVE_HEADERS = {
    "authorization",
    "x-goog-api-key",
    "x-ccg-token",
    "cookie",
    "set-cookie",
}


def _mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}***{value[-4:]}"


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a redacted copy of headers for safe logging."""

    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = _mask_value(str(value))
        else:
            redacted[key] = value
    return redacted


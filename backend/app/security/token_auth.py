from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


def get_gateway_token_from_headers(request: Request) -> str | None:
    header_name = settings.CCG_AUTH_HEADER_NAME
    return request.headers.get(header_name)


async def require_gateway_auth(request: Request) -> None:
    if not settings.CCG_AUTH_ENABLED:
        return

    token = get_gateway_token_from_headers(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing gateway token",
        )

    if token != settings.CCG_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid gateway token",
        )


RequireGatewayAuth = Depends(require_gateway_auth)


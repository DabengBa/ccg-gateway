from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
import httpx

from app.services.routing_service import RoutingService
from app.services.proxy_service import ProxyService
from app.core.database import async_session_maker
from app.security.token_auth import require_gateway_auth

proxy_router = APIRouter(dependencies=[Depends(require_gateway_auth)])


@proxy_router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy_request(request: Request, path: str):
    async with async_session_maker() as db:
        routing_service = RoutingService(db)
        proxy_service = ProxyService(db, routing_service)
        return await proxy_service.forward_request(request, path)

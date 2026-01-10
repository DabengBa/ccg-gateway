from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
import json
import time
import logging
import asyncio
from typing import Optional, AsyncIterator
from urllib.parse import quote

from app.services.routing_service import RoutingService
from app.services.provider_service import ProviderService
from app.services.stats_service import StatsService
from app.models.models import Provider, TimeoutSettings, GatewaySettings
from sqlalchemy import select

logger = logging.getLogger(__name__)


def _mask_key(key: str) -> str:
    """Mask API key for safe logging."""
    if len(key) <= 12:
        return "***"
    return f"{key[:6]}***{key[-4:]}"


def _truncate_body(body: bytes, max_len: int = 2000) -> str:
    """Truncate body for logging."""
    try:
        text = body.decode("utf-8")
        if len(text) <= max_len:
            return text
        return text[:max_len] + f"... [truncated, total {len(text)} chars]"
    except:
        return f"[binary data, {len(body)} bytes]"


def _safe_headers(headers: dict) -> dict:
    """Mask sensitive headers for logging."""
    safe = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            safe[k] = _mask_key(v) if v else ""
        else:
            safe[k] = v
    return safe

# Headers to filter out when forwarding
FILTERED_HEADERS = {
    "host", "connection", "keep-alive", "transfer-encoding",
    "te", "trailer", "upgrade"
}

# Shared HTTP client for connection pooling
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=None, write=30.0, pool=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    return _http_client


class ProxyService:
    def __init__(self, db: AsyncSession, routing_service: RoutingService):
        self.db = db
        self.routing_service = routing_service
        self.provider_service = ProviderService(db)
        self.stats_service = StatsService(db)

    async def forward_request(self, request: Request, path: str) -> Response:
        """Forward request to upstream provider."""
        start_time = time.time()

        # Detect CLI type from request
        cli_type = self._detect_cli_type(request, path)

        # Select provider
        provider = await self.routing_service.select_provider(cli_type)
        if not provider:
            raise HTTPException(status_code=503, detail="No available provider")

        # Get settings
        timeouts = await self._get_timeout_settings()
        debug_log = await self._get_debug_log()

        # Build upstream URL
        upstream_url = f"{provider.base_url.rstrip('/')}/{path}"
        if request.url.query:
            upstream_url += f"?{request.url.query}"

        # Prepare headers (filter hop-by-hop headers)
        headers = {
            k: v for k, v in request.headers.items()
            if k.lower() not in FILTERED_HEADERS
        }
        headers["authorization"] = f"Bearer {provider.api_key}"

        # Get request body
        body = await request.body()

        # Check if streaming
        is_stream = self._is_streaming_request(body)

        # Debug log: client request + forwarding request
        if debug_log:
            client_ip = request.client.host if request.client else "unknown"
            logger.info(
                f"\n{'='*60}\n"
                f"[DEBUG] === CLIENT REQUEST ===\n"
                f"  Client IP: {client_ip}\n"
                f"  Method: {request.method}\n"
                f"  Path: {path}\n"
                f"  Query: {request.url.query}\n"
                f"  Headers: {json.dumps(_safe_headers(dict(request.headers)), indent=2, ensure_ascii=False)}\n"
                f"  Body: {_truncate_body(body)}\n"
                f"[DEBUG] === FORWARD REQUEST ===\n"
                f"  Provider: {provider.name}\n"
                f"  Upstream URL: {upstream_url}\n"
                f"  Headers: {json.dumps(_safe_headers(headers), indent=2, ensure_ascii=False)}\n"
                f"  Stream: {is_stream}\n"
                f"{'='*60}"
            )

        try:
            if is_stream:
                return await self._forward_streaming(
                    provider, upstream_url, request.method, headers, body,
                    timeouts, cli_type, start_time, debug_log
                )
            else:
                return await self._forward_non_streaming(
                    provider, upstream_url, request.method, headers, body,
                    timeouts, cli_type, start_time, debug_log
                )
        except Exception as e:
            elapsed = (time.time() - start_time) * 1000
            logger.error(f"Proxy error for provider {provider.name}: {e}")
            if debug_log:
                logger.info(
                    f"\n[DEBUG] === ERROR ===\n"
                    f"  Provider: {provider.name}\n"
                    f"  Error: {e}\n"
                    f"  Elapsed: {elapsed:.2f}ms\n"
                )
            await self.provider_service.record_failure(provider.id)
            await self.stats_service.record_request(provider.id, cli_type, False)
            raise HTTPException(status_code=502, detail="Upstream request failed")

    async def _forward_streaming(
        self, provider: Provider, url: str, method: str,
        headers: dict, body: bytes, timeouts: TimeoutSettings,
        cli_type: str, start_time: float, debug_log: bool
    ) -> StreamingResponse:
        """Forward streaming request."""
        client = await get_http_client()

        # 先发起请求获取响应头和状态码
        req = client.build_request(method, url, headers=headers, content=body)
        response = await client.send(req, stream=True)

        if debug_log:
            logger.info(
                f"\n[DEBUG] === PROVIDER RESPONSE (streaming) ===\n"
                f"  Status: {response.status_code}\n"
                f"  Headers: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}"
            )

        # 错误响应直接返回
        if response.status_code >= 400:
            error_body = await response.aread()
            await response.aclose()
            if debug_log:
                elapsed = (time.time() - start_time) * 1000
                logger.info(f"\n[DEBUG] === ERROR RESPONSE ===\n  Body: {_truncate_body(error_body)}\n  Elapsed: {elapsed:.2f}ms\n")
            await self.provider_service.record_failure(provider.id)
            await self.stats_service.record_request(provider.id, cli_type, False)
            return Response(content=error_body, status_code=response.status_code, media_type=response.headers.get("content-type"))

        first_byte_time: Optional[float] = None
        total_bytes = 0

        async def stream_generator() -> AsyncIterator[bytes]:
            nonlocal first_byte_time, total_bytes
            first_byte_received = False
            success = False

            try:
                aiter = response.aiter_bytes()
                while True:
                    timeout_val = timeouts.stream_first_byte_timeout if not first_byte_received else timeouts.stream_idle_timeout
                    try:
                        chunk = await asyncio.wait_for(aiter.__anext__(), timeout=timeout_val)
                    except StopAsyncIteration:
                        success = True
                        break
                    except asyncio.TimeoutError:
                        timeout_type = "First byte" if not first_byte_received else "Idle"
                        logger.warning(f"{timeout_type} timeout for provider {provider.name}")
                        yield f'event: error\ndata: {{"type":"timeout","message":"{timeout_type} timeout"}}\n\n'.encode()
                        break

                    if not first_byte_received:
                        first_byte_received = True
                        first_byte_time = time.time()

                    total_bytes += len(chunk)
                    yield chunk

            except httpx.TimeoutException:
                logger.error(f"Timeout for provider {provider.name}")
                yield b'event: error\ndata: {"type":"timeout","message":"connection timeout"}\n\n'
            except Exception as e:
                logger.error(f"Streaming error for provider {provider.name}: {e}")
                yield f'event: error\ndata: {{"type":"error","message":"{str(e)}"}}\n\n'.encode()
            finally:
                await response.aclose()
                if success:
                    await self.provider_service.record_success(provider.id)
                    await self.stats_service.record_request(provider.id, cli_type, True)
                else:
                    await self.provider_service.record_failure(provider.id)
                    await self.stats_service.record_request(provider.id, cli_type, False)

                if debug_log:
                    elapsed = (time.time() - start_time) * 1000
                    ttfb = (first_byte_time - start_time) * 1000 if first_byte_time else 0
                    logger.info(
                        f"\n[DEBUG] === FORWARD RESULT (streaming) ===\n"
                        f"  Provider: {provider.name}\n"
                        f"  Success: {success}\n"
                        f"  Total Bytes: {total_bytes}\n"
                        f"  TTFB: {ttfb:.2f}ms\n"
                        f"  Total Elapsed: {elapsed:.2f}ms\n"
                    )

        # 透传上游响应头（过滤 hop-by-hop 头）
        resp_headers = {
            k: v for k, v in response.headers.items()
            if k.lower() not in FILTERED_HEADERS and k.lower() != "content-encoding"
        }
        # HTTP 头只支持 ASCII，中文名需要 URL 编码
        resp_headers["X-CCG-Provider"] = quote(provider.name, safe="")

        return StreamingResponse(
            stream_generator(),
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "text/event-stream"),
            headers=resp_headers
        )

    async def _forward_non_streaming(
        self, provider: Provider, url: str, method: str,
        headers: dict, body: bytes, timeouts: TimeoutSettings,
        cli_type: str, start_time: float, debug_log: bool
    ) -> Response:
        """Forward non-streaming request."""
        client = await get_http_client()
        timeout = httpx.Timeout(connect=10.0, read=timeouts.non_stream_timeout, write=30.0, pool=10.0)

        try:
            response = await client.request(method, url, headers=headers, content=body, timeout=timeout)
            elapsed = (time.time() - start_time) * 1000

            if debug_log:
                logger.info(
                    f"\n[DEBUG] === PROVIDER RESPONSE ===\n"
                    f"  Status: {response.status_code}\n"
                    f"  Headers: {json.dumps(dict(response.headers), indent=2, ensure_ascii=False)}\n"
                    f"  Body: {_truncate_body(response.content)}\n"
                    f"[DEBUG] === FORWARD RESULT ===\n"
                    f"  Provider: {provider.name}\n"
                    f"  Status: {response.status_code}\n"
                    f"  Response Size: {len(response.content)} bytes\n"
                    f"  Elapsed: {elapsed:.2f}ms\n"
                )

            if response.status_code >= 400:
                await self.provider_service.record_failure(provider.id)
                await self.stats_service.record_request(provider.id, cli_type, False)
            else:
                await self.provider_service.record_success(provider.id)
                await self.stats_service.record_request(provider.id, cli_type, True)

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )

        except httpx.TimeoutException:
            elapsed = (time.time() - start_time) * 1000
            if debug_log:
                logger.info(f"\n[DEBUG] Non-streaming timeout after {elapsed:.2f}ms\n")
            await self.provider_service.record_failure(provider.id)
            await self.stats_service.record_request(provider.id, cli_type, False)
            raise HTTPException(status_code=504, detail="Upstream timeout")

    def _detect_cli_type(self, request: Request, path: str) -> str:
        """Detect CLI type from request."""
        if "/v1/messages" in path or "anthropic" in path.lower():
            return "claude_code"
        if "/v1/chat/completions" in path:
            user_agent = request.headers.get("user-agent", "").lower()
            if "codex" in user_agent:
                return "codex"
            return "claude_code"
        if "gemini" in path.lower() or "generativelanguage" in path.lower():
            return "gemini"
        return "claude_code"

    def _is_streaming_request(self, body: bytes) -> bool:
        """Check if request is for streaming."""
        try:
            data = json.loads(body)
            return data.get("stream", False)
        except:
            return False

    async def _get_timeout_settings(self) -> TimeoutSettings:
        """Get timeout settings from database."""
        result = await self.db.execute(select(TimeoutSettings).where(TimeoutSettings.id == 1))
        settings = result.scalar_one_or_none()
        if not settings:
            return TimeoutSettings(
                stream_first_byte_timeout=30,
                stream_idle_timeout=60,
                non_stream_timeout=120
            )
        return settings

    async def _get_debug_log(self) -> bool:
        """Get debug_log setting from database."""
        result = await self.db.execute(select(GatewaySettings).where(GatewaySettings.id == 1))
        settings = result.scalar_one_or_none()
        return bool(settings.debug_log) if settings else False

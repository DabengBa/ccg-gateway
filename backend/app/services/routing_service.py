from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import time

from app.models.models import Provider


class RoutingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def select_provider(self, cli_type: str) -> Optional[Provider]:
        """Select provider by availability-first mode (by sort_order, not blacklisted)."""
        now = int(time.time())

        result = await self.db.execute(
            select(Provider)
            .where(Provider.enabled == 1)
            .where(Provider.cli_type == cli_type)
            .order_by(Provider.sort_order)
        )
        providers = result.scalars().all()

        for provider in providers:
            if not self._is_blacklisted(provider, now):
                return provider

        return None

    def _is_blacklisted(self, provider: Provider, now: int) -> bool:
        """Check if provider is blacklisted."""
        if provider.blacklisted_until is None:
            return False
        return provider.blacklisted_until > now

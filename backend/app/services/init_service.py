from sqlalchemy import select
import time

from app.core.database import async_session_maker
from app.models.models import GatewaySettings, TimeoutSettings, CliSettings


async def init_default_data():
    """Initialize default data in database."""
    async with async_session_maker() as db:
        now = int(time.time())

        # Initialize gateway settings
        result = await db.execute(select(GatewaySettings).where(GatewaySettings.id == 1))
        if not result.scalar_one_or_none():
            gateway = GatewaySettings(id=1, updated_at=now)
            db.add(gateway)

        # Initialize timeout settings
        result = await db.execute(select(TimeoutSettings).where(TimeoutSettings.id == 1))
        if not result.scalar_one_or_none():
            timeout = TimeoutSettings(
                id=1,
                stream_first_byte_timeout=30,
                stream_idle_timeout=60,
                non_stream_timeout=120,
                updated_at=now
            )
            db.add(timeout)

        # Initialize CLI settings
        for cli_type in ["claude_code", "codex", "gemini"]:
            result = await db.execute(
                select(CliSettings).where(CliSettings.cli_type == cli_type)
            )
            if not result.scalar_one_or_none():
                cli = CliSettings(
                    cli_type=cli_type,
                    routing_mode="availability",
                    default_json_config="{}",
                    updated_at=now
                )
                db.add(cli)

        await db.commit()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
import time

from app.models.models import McpConfig, McpCliFlag
from app.schemas.schemas import McpCreate, McpUpdate, McpResponse
from app.services.cli_sync_service import sync_mcp_to_cli, remove_mcp_from_all_cli, sync_mcp_to_claude, sync_mcp_to_codex, sync_mcp_to_gemini


class McpService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_mcp(self) -> List[McpResponse]:
        result = await self.db.execute(
            select(McpConfig).options(selectinload(McpConfig.cli_flags))
        )
        mcps = result.scalars().all()

        responses = []
        for mcp in mcps:
            cli_flags = {f.cli_type: bool(f.enabled) for f in mcp.cli_flags}
            responses.append(McpResponse(
                id=mcp.id,
                name=mcp.name,
                config_json=mcp.config_json,
                enabled=bool(mcp.enabled),
                cli_flags=cli_flags
            ))
        return responses

    async def get_mcp(self, mcp_id: int) -> Optional[McpResponse]:
        result = await self.db.execute(
            select(McpConfig)
            .options(selectinload(McpConfig.cli_flags))
            .where(McpConfig.id == mcp_id)
        )
        mcp = result.scalar_one_or_none()
        if not mcp:
            return None

        cli_flags = {f.cli_type: bool(f.enabled) for f in mcp.cli_flags}
        return McpResponse(
            id=mcp.id,
            name=mcp.name,
            config_json=mcp.config_json,
            enabled=bool(mcp.enabled),
            cli_flags=cli_flags
        )

    async def create_mcp(self, data: McpCreate) -> McpResponse:
        now = int(time.time())

        mcp = McpConfig(
            name=data.name,
            config_json=data.config_json,
            enabled=1 if data.enabled else 0,
            updated_at=now
        )
        self.db.add(mcp)
        await self.db.flush()

        cli_flags_dict = {
            "claude_code": data.cli_flags.claude_code,
            "codex": data.cli_flags.codex,
            "gemini": data.cli_flags.gemini
        }

        # Add CLI flags
        for cli_type, enabled in cli_flags_dict.items():
            flag = McpCliFlag(
                mcp_id=mcp.id,
                cli_type=cli_type,
                enabled=1 if enabled else 0
            )
            self.db.add(flag)

        await self.db.commit()

        # Sync to CLI config files (new MCP, no old flags)
        sync_mcp_to_cli(data.name, data.config_json, cli_flags_dict, None)

        return await self.get_mcp(mcp.id)

    async def update_mcp(self, mcp_id: int, data: McpUpdate) -> Optional[McpResponse]:
        result = await self.db.execute(
            select(McpConfig)
            .options(selectinload(McpConfig.cli_flags))
            .where(McpConfig.id == mcp_id)
        )
        mcp = result.scalar_one_or_none()
        if not mcp:
            return None

        now = int(time.time())

        # Save old cli_flags state for comparison
        old_cli_flags = {f.cli_type: bool(f.enabled) for f in mcp.cli_flags}
        config_changed = data.config_json is not None and data.config_json != mcp.config_json

        if data.name is not None:
            mcp.name = data.name
        if data.config_json is not None:
            mcp.config_json = data.config_json
        if data.enabled is not None:
            mcp.enabled = 1 if data.enabled else 0
        mcp.updated_at = now

        # Update CLI flags if provided
        cli_flags_dict = None
        if data.cli_flags is not None:
            await self.db.execute(
                delete(McpCliFlag).where(McpCliFlag.mcp_id == mcp_id)
            )
            cli_flags_dict = {
                "claude_code": data.cli_flags.claude_code,
                "codex": data.cli_flags.codex,
                "gemini": data.cli_flags.gemini
            }
            for cli_type, enabled in cli_flags_dict.items():
                flag = McpCliFlag(
                    mcp_id=mcp_id,
                    cli_type=cli_type,
                    enabled=1 if enabled else 0
                )
                self.db.add(flag)

        await self.db.commit()

        # Sync to CLI config files
        if cli_flags_dict is not None:
            # CLI flags changed, sync only changed ones
            sync_mcp_to_cli(mcp.name, mcp.config_json, cli_flags_dict, old_cli_flags)
        elif config_changed:
            # Config changed but CLI flags not changed, sync to all enabled CLIs
            if old_cli_flags.get("claude_code"):
                sync_mcp_to_claude(mcp.name, mcp.config_json, True)
            if old_cli_flags.get("codex"):
                sync_mcp_to_codex(mcp.name, mcp.config_json, True)
            if old_cli_flags.get("gemini"):
                sync_mcp_to_gemini(mcp.name, mcp.config_json, True)

        return await self.get_mcp(mcp_id)

    async def delete_mcp(self, mcp_id: int) -> bool:
        result = await self.db.execute(
            select(McpConfig)
            .options(selectinload(McpConfig.cli_flags))
            .where(McpConfig.id == mcp_id)
        )
        mcp = result.scalar_one_or_none()
        if not mcp:
            return False

        mcp_name = mcp.name

        await self.db.delete(mcp)
        await self.db.commit()

        # Remove from all CLI config files
        remove_mcp_from_all_cli(mcp_name)

        return True

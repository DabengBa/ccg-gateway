from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from typing import List, Optional
import time

from app.models.models import PromptPreset, PromptCliFlag
from app.schemas.schemas import PromptCreate, PromptUpdate, PromptResponse
from app.services.cli_sync_service import sync_prompt_to_cli, sync_prompt_to_file, get_claude_prompt_path, get_codex_prompt_path, get_gemini_prompt_path


class PromptService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_prompts(self) -> List[PromptResponse]:
        result = await self.db.execute(
            select(PromptPreset).options(selectinload(PromptPreset.cli_flags))
        )
        prompts = result.scalars().all()

        responses = []
        for prompt in prompts:
            cli_flags = {f.cli_type: bool(f.enabled) for f in prompt.cli_flags}
            responses.append(PromptResponse(
                id=prompt.id,
                name=prompt.name,
                content=prompt.content,
                enabled=bool(prompt.enabled),
                cli_flags=cli_flags
            ))
        return responses

    async def get_prompt(self, prompt_id: int) -> Optional[PromptResponse]:
        result = await self.db.execute(
            select(PromptPreset)
            .options(selectinload(PromptPreset.cli_flags))
            .where(PromptPreset.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            return None

        cli_flags = {f.cli_type: bool(f.enabled) for f in prompt.cli_flags}
        return PromptResponse(
            id=prompt.id,
            name=prompt.name,
            content=prompt.content,
            enabled=bool(prompt.enabled),
            cli_flags=cli_flags
        )

    async def _disable_other_prompts_for_cli(self, prompt_id: int, cli_type: str):
        """Disable the same CLI type for all other prompts (mutual exclusion)"""
        await self.db.execute(
            update(PromptCliFlag)
            .where(PromptCliFlag.cli_type == cli_type)
            .where(PromptCliFlag.prompt_id != prompt_id)
            .values(enabled=0)
        )

    async def create_prompt(self, data: PromptCreate) -> PromptResponse:
        now = int(time.time())

        prompt = PromptPreset(
            name=data.name,
            content=data.content,
            enabled=1 if data.enabled else 0,
            updated_at=now
        )
        self.db.add(prompt)
        await self.db.flush()

        cli_flags_dict = {
            "claude_code": data.cli_flags.claude_code,
            "codex": data.cli_flags.codex,
            "gemini": data.cli_flags.gemini
        }

        # Add CLI flags
        for cli_type, enabled in cli_flags_dict.items():
            flag = PromptCliFlag(
                prompt_id=prompt.id,
                cli_type=cli_type,
                enabled=1 if enabled else 0
            )
            self.db.add(flag)
            # Mutual exclusion: disable same CLI type for other prompts
            if enabled:
                await self._disable_other_prompts_for_cli(prompt.id, cli_type)

        await self.db.commit()

        # Sync to CLI config files (new prompt, no old flags)
        sync_prompt_to_cli(data.name, data.content, cli_flags_dict, None)

        return await self.get_prompt(prompt.id)

    async def update_prompt(self, prompt_id: int, data: PromptUpdate) -> Optional[PromptResponse]:
        result = await self.db.execute(
            select(PromptPreset)
            .options(selectinload(PromptPreset.cli_flags))
            .where(PromptPreset.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            return None

        now = int(time.time())

        # Save old cli_flags state for comparison
        old_cli_flags = {f.cli_type: bool(f.enabled) for f in prompt.cli_flags}
        content_changed = data.content is not None and data.content != prompt.content

        if data.name is not None:
            prompt.name = data.name
        if data.content is not None:
            prompt.content = data.content
        if data.enabled is not None:
            prompt.enabled = 1 if data.enabled else 0
        prompt.updated_at = now

        # Update CLI flags if provided
        cli_flags_dict = None
        if data.cli_flags is not None:
            await self.db.execute(
                delete(PromptCliFlag).where(PromptCliFlag.prompt_id == prompt_id)
            )
            cli_flags_dict = {
                "claude_code": data.cli_flags.claude_code,
                "codex": data.cli_flags.codex,
                "gemini": data.cli_flags.gemini
            }
            for cli_type, enabled in cli_flags_dict.items():
                flag = PromptCliFlag(
                    prompt_id=prompt_id,
                    cli_type=cli_type,
                    enabled=1 if enabled else 0
                )
                self.db.add(flag)
                # Mutual exclusion: disable same CLI type for other prompts
                if enabled:
                    await self._disable_other_prompts_for_cli(prompt_id, cli_type)

        await self.db.commit()

        # Sync to CLI config files
        if cli_flags_dict is not None:
            # CLI flags changed, sync only changed ones
            sync_prompt_to_cli(prompt.name, prompt.content, cli_flags_dict, old_cli_flags)
        elif content_changed:
            # Content changed but CLI flags not changed, sync to all enabled CLIs
            if old_cli_flags.get("claude_code"):
                sync_prompt_to_file(get_claude_prompt_path(), prompt.content, True)
            if old_cli_flags.get("codex"):
                sync_prompt_to_file(get_codex_prompt_path(), prompt.content, True)
            if old_cli_flags.get("gemini"):
                sync_prompt_to_file(get_gemini_prompt_path(), prompt.content, True)

        return await self.get_prompt(prompt_id)

    async def delete_prompt(self, prompt_id: int) -> bool:
        result = await self.db.execute(
            select(PromptPreset)
            .options(selectinload(PromptPreset.cli_flags))
            .where(PromptPreset.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            return False

        await self.db.delete(prompt)
        await self.db.commit()
        return True

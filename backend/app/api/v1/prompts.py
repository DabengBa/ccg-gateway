from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.schemas import PromptCreate, PromptUpdate, PromptResponse
from app.services.prompt_service import PromptService

router = APIRouter()


@router.get("", response_model=List[PromptResponse])
async def list_prompts(db: AsyncSession = Depends(get_db)):
    service = PromptService(db)
    return await service.list_prompts()


@router.post("", response_model=PromptResponse)
async def create_prompt(data: PromptCreate, db: AsyncSession = Depends(get_db)):
    service = PromptService(db)
    return await service.create_prompt(data)


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    service = PromptService(db)
    prompt = await service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(prompt_id: int, data: PromptUpdate, db: AsyncSession = Depends(get_db)):
    service = PromptService(db)
    prompt = await service.update_prompt(prompt_id, data)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: int, db: AsyncSession = Depends(get_db)):
    service = PromptService(db)
    success = await service.delete_prompt(prompt_id)
    if not success:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"message": "Prompt deleted"}

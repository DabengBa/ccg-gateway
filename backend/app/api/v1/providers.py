from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.schemas.schemas import (
    ProviderCreate, ProviderUpdate, ProviderResponse, ProviderReorder
)
from app.services.provider_service import ProviderService

router = APIRouter()


@router.get("", response_model=List[ProviderResponse])
async def list_providers(cli_type: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    return await service.list_providers(cli_type)


@router.post("", response_model=ProviderResponse)
async def create_provider(data: ProviderCreate, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    return await service.create_provider(data)


@router.get("/{provider_id}", response_model=ProviderResponse)
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    provider = await service.get_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: int, data: ProviderUpdate, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    provider = await service.update_provider(provider_id, data)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@router.delete("/{provider_id}")
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    success = await service.delete_provider(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider deleted"}


@router.post("/reorder")
async def reorder_providers(data: ProviderReorder, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    await service.reorder_providers(data.ids)
    return {"message": "Providers reordered"}


@router.post("/{provider_id}/reset-failures")
async def reset_failures(provider_id: int, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    success = await service.reset_failures(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Failures reset"}


@router.post("/{provider_id}/unblacklist")
async def unblacklist_provider(provider_id: int, db: AsyncSession = Depends(get_db)):
    service = ProviderService(db)
    success = await service.unblacklist(provider_id)
    if not success:
        raise HTTPException(status_code=404, detail="Provider not found")
    return {"message": "Provider unblacklisted"}

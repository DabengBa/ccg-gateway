from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.schemas.schemas import McpCreate, McpUpdate, McpResponse
from app.services.mcp_service import McpService

router = APIRouter()


@router.get("", response_model=List[McpResponse])
async def list_mcp(db: AsyncSession = Depends(get_db)):
    service = McpService(db)
    return await service.list_mcp()


@router.post("", response_model=McpResponse)
async def create_mcp(data: McpCreate, db: AsyncSession = Depends(get_db)):
    service = McpService(db)
    return await service.create_mcp(data)


@router.get("/{mcp_id}", response_model=McpResponse)
async def get_mcp(mcp_id: int, db: AsyncSession = Depends(get_db)):
    service = McpService(db)
    mcp = await service.get_mcp(mcp_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.put("/{mcp_id}", response_model=McpResponse)
async def update_mcp(mcp_id: int, data: McpUpdate, db: AsyncSession = Depends(get_db)):
    service = McpService(db)
    mcp = await service.update_mcp(mcp_id, data)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP not found")
    return mcp


@router.delete("/{mcp_id}")
async def delete_mcp(mcp_id: int, db: AsyncSession = Depends(get_db)):
    service = McpService(db)
    success = await service.delete_mcp(mcp_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP not found")
    return {"message": "MCP deleted"}

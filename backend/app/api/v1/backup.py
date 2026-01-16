from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.schemas import WebdavSettingsResponse, WebdavSettingsUpdate, WebdavTestRequest
from app.services import backup_service

router = APIRouter()


@router.get("/webdav", response_model=WebdavSettingsResponse)
async def get_webdav_settings(db: AsyncSession = Depends(get_db)):
    settings = await backup_service.get_webdav_settings(db)
    return settings


@router.put("/webdav", response_model=WebdavSettingsResponse)
async def update_webdav_settings(data: WebdavSettingsUpdate, db: AsyncSession = Depends(get_db)):
    settings = await backup_service.update_webdav_settings(
        db, url=data.url, username=data.username, password=data.password
    )
    return settings


@router.post("/webdav/test")
async def test_webdav_connection(data: WebdavTestRequest):
    try:
        result = backup_service.test_webdav_connection(data.url, data.username, data.password)
        return {"success": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/export/local")
async def export_to_local():
    try:
        backup_path = await backup_service.export_to_local()
        return FileResponse(
            path=str(backup_path),
            filename=backup_path.name,
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/local")
async def import_from_local(file: UploadFile = File(...)):
    if not file.filename.endswith(".db"):
        raise HTTPException(status_code=400, detail="Invalid file type, must be .db file")
    try:
        content = await file.read()
        await backup_service.import_from_local(content)
        return {"success": True, "message": "Database imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/webdav")
async def export_to_webdav(db: AsyncSession = Depends(get_db)):
    try:
        filename = await backup_service.export_to_webdav(db)
        return {"success": True, "filename": filename}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/webdav/list")
async def list_webdav_backups(db: AsyncSession = Depends(get_db)):
    try:
        backups = await backup_service.list_webdav_backups(db)
        return {"backups": backups}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/webdav")
async def import_from_webdav(filename: str, db: AsyncSession = Depends(get_db)):
    try:
        await backup_service.import_from_webdav(db, filename)
        return {"success": True, "message": "Database imported successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

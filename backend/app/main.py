import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

from app.core.config import settings
from app.core.database import init_db
from app.core.uptime import init_start_time
from app.api.admin import admin_router
from app.api.proxy import proxy_router
from app.services.init_service import init_default_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_start_time()
    await init_db()
    await init_default_data()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(admin_router, prefix="/admin/v1")
app.include_router(proxy_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.core.config import settings, DATA_DIR


class Base(DeclarativeBase):
    pass


# Create async engine
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DATA_DIR}/ccg_gateway.db",
    echo=False,
    connect_args={"check_same_thread": False}
)

# Session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


def _run_migrations(conn):
    """Run database migrations for schema changes."""
    result = conn.execute(text("PRAGMA table_info(providers)"))
    columns = [row[1] for row in result.fetchall()]

    if columns and "cli_type" not in columns:
        conn.execute(text(
            "ALTER TABLE providers ADD COLUMN cli_type VARCHAR(20) NOT NULL DEFAULT 'claude_code'"
        ))


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(_run_migrations)
        await conn.run_sync(Base.metadata.create_all)

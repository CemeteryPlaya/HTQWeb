"""Database setup for Admin."""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.settings import settings

engine = create_async_engine(
    settings.db_dsn,
    pool_size=10,
    max_overflow=20,
    connect_args={
        "server_settings": {
            "search_path": settings.db_schema,
        },
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

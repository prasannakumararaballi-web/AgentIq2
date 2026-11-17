"""Database engine, session management, and health verification."""

import logging
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from apps.api.config import settings

logger = logging.getLogger("agentiq.db")

# Global async engine and session factory
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine(url: str | None = None) -> AsyncEngine:
    """Return or initialize singleton async database engine."""
    global _async_engine
    if _async_engine is None or (url and str(_async_engine.url) != url):
        target_url = url or settings.database_url
        _async_engine = create_async_engine(
            target_url,
            echo=settings.db_echo,
            pool_pre_ping=settings.db_pool_pre_ping,
        )
    return _async_engine


def get_async_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return or initialize async session factory."""
    global _async_session_factory
    eng = engine or get_async_engine()
    if _async_session_factory is None or _async_session_factory.kw.get("bind") != eng:
        _async_session_factory = async_sessionmaker(
            bind=eng,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an isolated transaction-managed async session."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_health() -> dict[str, str | bool]:
    """Execute a lightweight SQL query to verify database connectivity."""
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                return {"connected": True, "status": "healthy"}
            return {"connected": False, "status": "unexpected_result"}
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        return {"connected": False, "status": "unreachable", "error": str(exc)}


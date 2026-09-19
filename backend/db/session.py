"""
Async SQLAlchemy engine and session factory.

Usage (in a FastAPI route):

    from db.session import get_db

    @router.get("/workflows")
    async def list_workflows(db: AsyncSession = Depends(get_db)):
        ...
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=(settings.environment == "development"))

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

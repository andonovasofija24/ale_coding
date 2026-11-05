from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# "Run tests" and submissions give their connection back while the code runner works (grading.run_task_tests,
# submission_queue), so a modest pool serves a whole exam; pre_ping drops connections the database closed.
engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_size=settings.DB_POOL_SIZE,
                             max_overflow=settings.DB_MAX_OVERFLOW, pool_timeout=30, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

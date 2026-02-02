from typing import Optional
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, DateTime

from server.config import settings


class Base(DeclarativeBase):
    pass


class UserPersona(Base):
    __tablename__ = "user_personas"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    extracted_keywords: Mapped[dict] = mapped_column(JSONB, default={})
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


if not settings.POSTGRESQL_DSN:
    raise ValueError("POSTGRESQL_DSN is not set in the environment variables.")

postgresql_engine = create_async_engine(settings.POSTGRESQL_DSN)
_AsyncSessionLocal = async_sessionmaker(postgresql_engine, expire_on_commit=False)


async def upsert_persona(user_id: str, new_data: dict) -> None:
    async with _AsyncSessionLocal() as session:
        stmt = insert(UserPersona).values(user_id=user_id, extracted_keywords=new_data)

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "extracted_keywords": UserPersona.extracted_keywords.concat(new_data),
                "updated_at": func.now(),
            },
        )
        await session.execute(upsert_stmt)
        await session.commit()


async def get_persona(user_id: str) -> Optional[UserPersona]:
    async with _AsyncSessionLocal() as session:
        return await session.get(UserPersona, user_id)

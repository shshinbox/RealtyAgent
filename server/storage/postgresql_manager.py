from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import CursorResult, func, DateTime, select, delete, update
from datetime import datetime


class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""

    pass


class UserPersona(Base):
    """사용자 페르소나 테이블"""

    __tablename__ = "user_personas"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    extracted_keywords: Mapped[dict] = mapped_column(JSONB, default={})
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now()
    )


class PostgreSQLManager:
    """PostgreSQL 비동기 데이터베이스 매니저"""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        """
        Args:
            database_url: PostgreSQL 연결 URL
            echo: SQL 로깅 여부
            pool_size: 커넥션 풀 크기
            max_overflow: 최대 추가 커넥션 수
        """
        if not database_url:
            raise ValueError("database_url is required")

        self.engine: AsyncEngine = create_async_engine(
            database_url, echo=echo, pool_size=pool_size, max_overflow=max_overflow
        )

        self.async_session_maker = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    @asynccontextmanager
    async def get_session(self):
        """세션 컨텍스트 매니저"""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def upsert_persona(self, user_id: str, new_data: Dict[str, Any]) -> None:
        """
        사용자 페르소나 업서트

        Args:
            user_id: 사용자 ID
            new_data: 추가할 키워드 데이터
        """
        async with self.get_session() as session:
            stmt = insert(UserPersona).values(
                user_id=user_id, extracted_keywords=new_data
            )

            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["user_id"],
                set_={
                    "extracted_keywords": UserPersona.extracted_keywords.concat(
                        new_data
                    ),
                    "updated_at": func.now(),
                },
            )

            await session.execute(upsert_stmt)

    async def get_persona(self, user_id: str) -> Optional[UserPersona]:
        """
        사용자 페르소나 조회

        Args:
            user_id: 사용자 ID

        Returns:
            UserPersona 객체 또는 None
        """
        async with self.get_session() as session:
            return await session.get(UserPersona, user_id)

    async def get_persona_dict(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        사용자 페르소나 딕셔너리 형태로 조회

        Args:
            user_id: 사용자 ID

        Returns:
            페르소나 데이터 딕셔너리 또는 None
        """
        persona = await self.get_persona(user_id)

        if persona:
            return {
                "user_id": persona.user_id,
                "extracted_keywords": persona.extracted_keywords,
                "updated_at": (
                    persona.updated_at.isoformat() if persona.updated_at else None
                ),
            }

        return None

    async def get_all_personas(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[UserPersona]:
        """
        모든 페르소나 조회

        Args:
            limit: 최대 조회 개수
            offset: 건너뛸 개수

        Returns:
            UserPersona 리스트
        """
        async with self.get_session() as session:
            stmt = select(UserPersona).offset(offset)

            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def update_persona_keywords(
        self, user_id: str, keywords: Dict[str, Any], merge: bool = True
    ) -> bool:
        """
        페르소나 키워드 업데이트

        Args:
            user_id: 사용자 ID
            keywords: 업데이트할 키워드
            merge: True면 기존 데이터와 병합, False면 덮어쓰기

        Returns:
            업데이트 성공 여부
        """
        async with self.get_session() as session:
            if merge:
                # 기존 데이터와 병합
                stmt = (
                    update(UserPersona)
                    .where(UserPersona.user_id == user_id)
                    .values(
                        extracted_keywords=UserPersona.extracted_keywords.concat(
                            keywords
                        ),
                        updated_at=func.now(),
                    )
                )
            else:
                # 덮어쓰기
                stmt = (
                    update(UserPersona)
                    .where(UserPersona.user_id == user_id)
                    .values(extracted_keywords=keywords, updated_at=func.now())
                )

            result = await session.execute(stmt)
            return result is not None

    async def delete_persona(self, user_id: str) -> bool:
        """
        페르소나 삭제

        Args:
            user_id: 사용자 ID

        Returns:
            삭제 성공 여부
        """
        async with self.get_session() as session:
            stmt = delete(UserPersona).where(UserPersona.user_id == user_id)
            result = await session.execute(stmt)
            return result is not None

    async def persona_exists(self, user_id: str) -> bool:
        """
        페르소나 존재 확인

        Args:
            user_id: 사용자 ID

        Returns:
            존재 여부
        """
        persona = await self.get_persona(user_id)
        return persona is not None

    async def count_personas(self) -> int:
        """전체 페르소나 개수 조회"""
        async with self.get_session() as session:
            stmt = select(func.count()).select_from(UserPersona)
            result = await session.execute(stmt)
            return result.scalar_one()

    async def search_by_keyword(
        self, keyword: str, limit: int = 10
    ) -> List[UserPersona]:
        """
        키워드로 페르소나 검색 (JSONB contains 사용)

        Args:
            keyword: 검색할 키워드
            limit: 최대 조회 개수

        Returns:
            UserPersona 리스트
        """
        async with self.get_session() as session:
            # JSONB에서 키 존재 여부 확인
            stmt = (
                select(UserPersona)
                .where(UserPersona.extracted_keywords.has_key(keyword))
                .limit(limit)
            )

            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def batch_upsert_personas(self, personas: List[Dict[str, Any]]) -> None:
        """
        여러 페르소나 일괄 업서트

        Args:
            personas: 페르소나 데이터 리스트
                     예: [{"user_id": "user1", "extracted_keywords": {...}}, ...]
        """
        async with self.get_session() as session:
            for persona_data in personas:
                stmt = insert(UserPersona).values(**persona_data)

                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id"],
                    set_={
                        "extracted_keywords": UserPersona.extracted_keywords.concat(
                            persona_data["extracted_keywords"]
                        ),
                        "updated_at": func.now(),
                    },
                )

                await session.execute(upsert_stmt)

    async def close(self):
        await self.engine.dispose()

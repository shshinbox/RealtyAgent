import asyncio
import json
import logging
import os

import redis.asyncio as aioredis
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import func

from .extractor import PersonaExtractor
from server.storage.postgresql_manager import UserPersona

logger = logging.getLogger(__name__)

QUEUE_NAME = "memory_queue"


async def process_task(task: dict, pg_session_maker, extractor: PersonaExtractor):
    user_id = task.get("user_id")
    refined_query = task.get("refined_query", "")
    final_answer = task.get("final_answer", "")

    if not user_id:
        logger.warning("[Worker] Task missing user_id, skipping.")
        return

    text = f"{refined_query} {final_answer}".strip()
    entities = extractor.extract(text)

    if not entities:
        logger.info(f"[Worker] No entities extracted for user: {user_id}")
        return

    async with pg_session_maker() as session:
        stmt = insert(UserPersona).values(user_id=user_id, extracted_keywords=entities)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["user_id"],
            set_={
                "extracted_keywords": UserPersona.extracted_keywords.concat(entities),
                "updated_at": func.now(),
            },
        )
        await session.execute(upsert_stmt)
        await session.commit()

    logger.info(f"[Worker] Persona updated | user: {user_id} | entities: {entities}")


async def run_worker():
    redis_url = os.environ["REDIS_URL"]
    postgresql_url = os.environ["POSTGRESQL_URL"]

    redis: aioredis.Redis = aioredis.from_url(redis_url, decode_responses=True)
    engine = create_async_engine(postgresql_url)
    pg_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    extractor = PersonaExtractor()

    logger.info("[Worker] Started. Listening to queue: %s", QUEUE_NAME)

    try:
        while True:
            result = await redis.blpop(QUEUE_NAME, timeout=5)
            if not result:
                continue

            _, raw = result
            task = json.loads(raw)
            logger.info(f"[Worker] Task received: thread_id={task.get('thread_id')}")

            try:
                await process_task(task, pg_session_maker, extractor)
            except Exception as e:
                logger.error(f"[Worker] Failed to process task: {e}")
    finally:
        await redis.close()
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())

import redis.asyncio as aioredis
import json

from redis.asyncio import Redis

from ..config import settings
from ..logger import logger


if not settings.REDIS_URL:
    raise ValueError("REDIS_URL is not set in the environment variables.")

redis_client: Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def push_task(queue_name: str, data: dict):
    await redis_client.rpush(queue_name, json.dumps(data))


async def run_redis_worker(queue_name: str):
    logger.info(f"[*] Worker monitoring queue: {queue_name}")
    while True:
        _, task_data = await redis_client.blpop(queue_name, timeout=0)
        task = json.loads(task_data)

        logger.info(f"[Worker] Processing task for user: {task.get('user_id')}")

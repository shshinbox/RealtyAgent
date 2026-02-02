from ..storage.redis_client import push_task
from ..storage.postgresql_client import get_persona


async def get_user_persona(user_id: str, db_engine) -> dict:
    user = await get_persona(user_id=user_id)
    return user.extracted_keywords if user else {}


async def enqueue_memory_task(data: dict, redis_client) -> None:
    if data:
        await push_task(queue_name="task_queue", data=data)

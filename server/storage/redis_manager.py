from typing import Optional, List, Dict, Any
import redis.asyncio as redis
import json


class RedisManager:
    """Redis 비동기 매니저"""

    def __init__(self, redis_url: str):
        if not redis_url:
            raise ValueError("redis_url is required")

        self.client: redis.Redis = redis.from_url(redis_url, decode_responses=True)

    # ---------- 기본 KV ----------

    async def set_json(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ):
        data = json.dumps(value)
        if ttl:
            await self.client.set(key, data, ex=ttl)
        else:
            await self.client.set(key, data)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def delete(self, key: str) -> bool:
        return await self.client.delete(key) > 0

    async def exists(self, key: str) -> bool:
        return await self.client.exists(key) > 0

    # ---------- Queue (List) ----------

    async def push_task(self, queue_name: str, data: Dict[str, Any]):
        await self.client.rpush(queue_name, json.dumps(data))

    async def pop_task(
        self, queue_name: str, timeout: int = 0
    ) -> Optional[Dict[str, Any]]:
        result = await self.client.blpop(queue_name, timeout=timeout)
        if not result:
            return None

        _, task_data = result
        return json.loads(task_data)

    # ---------- Hash ----------

    async def hset_json(self, name: str, key: str, value: Dict[str, Any]):
        await self.client.hset(name, key, json.dumps(value))

    async def hget_json(self, name: str, key: str) -> Optional[Dict[str, Any]]:
        data = await self.client.hget(name, key)
        return json.loads(data) if data else None

    async def hgetall_json(self, name: str) -> Dict[str, Dict[str, Any]]:
        raw = await self.client.hgetall(name)
        return {k: json.loads(v) for k, v in raw.items()}

    # ---------- Set ----------

    async def sadd(self, name: str, value: str):
        await self.client.sadd(name, value)

    async def smembers(self, name: str) -> List[str]:
        return list(await self.client.smembers(name))

    # ---------- Close ----------

    async def close(self):
        await self.client.close()

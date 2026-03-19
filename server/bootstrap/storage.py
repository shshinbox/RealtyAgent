from dataclasses import dataclass

from server.config import Settings
from server.storage.redis_manager import RedisManager
from server.storage.postgresql_manager import PostgreSQLManager
from server.storage.qdrant_searcher import QdrantSearcher


@dataclass
class StorageBundle:
    redis: RedisManager
    pg: PostgreSQLManager
    qdrant: QdrantSearcher


def build_storage(settings: Settings) -> StorageBundle:
    return StorageBundle(
        redis=RedisManager(settings.REDIS_URL or ""),
        pg=PostgreSQLManager(settings.POSTGRESQL_URL or ""),
        qdrant=QdrantSearcher(
            host=settings.QDRANT_HOST or "",
            port=settings.QDRANT_PORT or -1,
        ),
    )


async def close_storage(bundle: StorageBundle) -> None:
    await bundle.redis.close()
    await bundle.pg.close()
    await bundle.qdrant.close()

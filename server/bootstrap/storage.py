from dataclasses import dataclass

from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore

from server.config import Settings
from server.storage.redis_manager import RedisManager
from server.storage.postgresql_manager import Base, PostgreSQLManager
from server.storage.qdrant_searcher import QdrantSearcher


@dataclass
class StorageBundle:
    redis: RedisManager
    pg: PostgreSQLManager
    qdrant: QdrantSearcher
    neo4j: Neo4jPropertyGraphStore


async def build_storage(settings: Settings) -> StorageBundle:
    pg = PostgreSQLManager(settings.POSTGRESQL_URL or "")
    async with pg.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    return StorageBundle(
        redis=RedisManager(settings.REDIS_URL or ""),
        pg=pg,
        qdrant=QdrantSearcher(
            host=settings.QDRANT_HOST or "",
            port=settings.QDRANT_PORT or -1,
        ),
        neo4j=Neo4jPropertyGraphStore(
            username=settings.NEO4J_USERNAME or "",
            password=settings.NEO4J_PASSWORD or "",
            url=settings.NEO4J_URL or "",
        ),
    )


async def close_storage(bundle: StorageBundle) -> None:
    await bundle.redis.close()
    await bundle.pg.close()
    await bundle.qdrant.close()  # AsyncQdrantClient.close() 직접 호출
    if hasattr(bundle.neo4j, "_driver"):
        bundle.neo4j._driver.close()

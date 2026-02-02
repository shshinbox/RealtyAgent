from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
import uuid

from ..config import settings

qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def upsert_vector_data(collection_name: str, vector: list, payload: dict):
    await qdrant_client.upsert(
        collection_name=collection_name,
        points=[PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload)],
    )


async def search_similar_docs(collection_name: str, query_vector: list, limit: int = 5):
    response = await qdrant_client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return [point.payload for point in response.points]

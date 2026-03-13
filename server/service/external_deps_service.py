from fastapi import Request
from typing import Any
from openai import AsyncOpenAI


class ExternalDeps:
    def __init__(self, request: Request):
        self.postgres = request.app.state.pg
        self.qdrant = request.app.state.qdrant
        self.redis = request.app.state.redis
        self.request = request

        settings = request.app.state.settings
        self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def get_user_persona(self, user_id: str):
        return await self.postgres.get_persona(user_id=user_id)

    async def search_memories(
        self,
        query: str,
        metadata_fields: list[str] = [],
        metadata_values: list[Any] = [],
        top_k: int = 5,
    ):
        query_vector = await self._query_vector(query)

        return await self.qdrant.search_with_metadata_filter(
            query_vector=query_vector,
            collection_name="user_memory",
            metadata_fields=metadata_fields,
            metadata_values=metadata_values,
            limit=top_k,
        )

    async def push_task(self, queue_name: str, data: dict):
        await self.redis.push_task(queue_name=queue_name, data=data)

    async def search_docs(
        self,
        query: str = "",
        metadata_fields: list[str] = [],
        metadata_values: list[Any] = [],
        top_k: int = 5,
    ):
        retriever = self.request.app.state.retriever
        return await retriever.search(query=query, top_k=top_k)

    async def _query_vector(self, query: str) -> list[float]:
        response = await self._openai.embeddings.create(
            model="text-embedding-3-small",
            input=query,
        )
        return response.data[0].embedding

from typing import Protocol, Any


class ExternalDepsPort(Protocol):
    async def get_user_persona(self, user_id: str): ...
    async def search_memories(
        self,
        query: str,
        metadata_fields: list[str] = [],
        metadata_values: list[Any] = [],
        top_k: int = 5,
    ): ...
    async def push_task(self, queue_name: str, data: dict): ...
    async def search_docs(
        self,
        query: str,
        metadata_fields: list[str] = [],
        metadata_values: list[Any] = [],
        top_k: int = 5,
    ): ...

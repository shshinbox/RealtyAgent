from abc import ABC, abstractmethod


class Renderer(ABC):
    @abstractmethod
    async def render(self, thread_id: str, content: str) -> str:
        pass

    @abstractmethod
    async def render_content(self, chunk: str, title: str) -> str:
        pass

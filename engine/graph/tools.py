import requests
from typing import List, Union
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
)
from .config import config_settings


class GuardPrompt:
    def __init__(self):
        self.BASE_URL = "https://api.lakera.ai/v2/guard"

    def is_secured(self, messages: List[BaseMessage]) -> bool:
        result = self._guard_messages(messages)
        return not result.get("flagged", False)

    def _guard_messages(self, messages: List[BaseMessage]) -> dict:
        lakera_messages = self._map_langchain_to_lakera(messages)

        session = requests.Session()
        response = session.post(
            self.BASE_URL,
            json={"messages": lakera_messages},
            headers={"Authorization": f"Bearer {config_settings.LAKERA_GUARD_API_KEY}"},
            timeout=5.0,
        )

        response.raise_for_status()
        return response.json()

    def _map_langchain_to_lakera(self, messages: List[BaseMessage]) -> List[dict]:
        mapped_messages = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = "user"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            elif isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, ToolMessage):
                role = "tool"
            else:
                role = getattr(msg, "role", "user")

            content = msg.content
            if isinstance(content, list):
                content = " ".join(
                    [c.get("text", "") for c in content if isinstance(c, dict)]
                )

            mapped_messages.append({"role": role, "content": str(content)})

        return mapped_messages


class HallucinationDetector:
    def __init__(self):
        self.BASE_URL = ""

from typing import Dict
from pydantic import SecretStr
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

from engine.graph.schema import NodeType
from server.config import Settings


def build_llm_map(settings: Settings) -> Dict[NodeType, BaseChatModel]:
    if not settings.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")

    def llm(model: str) -> BaseChatModel:
        return ChatOpenAI(
            model=model,
            api_key=SecretStr(settings.OPENAI_API_KEY or ""),
            temperature=0,
        )

    return {
        NodeType.PLANNER: llm("gpt-4o"),
        NodeType.GENERATOR: llm("gpt-4o-mini"),
        NodeType.DOC_RETRIEVER: llm("gpt-4o-mini"),
        NodeType.LEGAL_RETRIEVER: llm("gpt-4o-mini"),
        NodeType.HUMAN_REVIEWER: llm("gpt-4o-mini"),
        NodeType.COUNSELOR: llm("gpt-4o-mini"),
    }

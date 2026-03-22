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
        NodeType.PLANNER: llm("gpt-5.4-mini"),
        NodeType.GENERATOR: llm("gpt-5.4-mini"),
        NodeType.DOC_RETRIEVER: llm("gpt-5.4-mini"),
        NodeType.LEGAL_RETRIEVER: llm("gpt-5.4-mini"),
        NodeType.HUMAN_REVIEWER: llm("gpt-5.4-mini"),
        NodeType.COUNSELOR: llm("gpt-5.4-mini"),
    }

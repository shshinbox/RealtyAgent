from typing import List
import requests
from pydantic import ValidationError
from langchain_core.language_models import BaseChatModel

from ..utils import AgentSpecLoader
from ..config import config_settings
from ..schema import LegalSearchQuery, NodeType
from ..state import AgentState, StateKey
from .base import ToolNode


class LegalRetriever(ToolNode[LegalSearchQuery]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.LEGAL_RETRIEVER, LegalSearchQuery, llm)
        self.base_url = AgentSpecLoader.load_elements(self.key, "base_url")

    async def _execute_tool(self, args: LegalSearchQuery) -> dict:
        api_params = {
            "OC": config_settings.KOREAN_LAW_OC,
            "target": "expc",
            "type": "JSON",
            "query": args.keyword,
            **args.model_dump(exclude={"keyword"}, exclude_none=True),
        }

        response = requests.get(self.base_url, params=api_params, timeout=10)
        response.raise_for_status()
        return response.json()

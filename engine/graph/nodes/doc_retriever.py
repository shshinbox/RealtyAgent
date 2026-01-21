from typing import List
import requests
from pydantic import ValidationError
from langchain_core.language_models import BaseChatModel

from ..utils import AgentSpecLoader
from ..schema import LegalSearchQuery, NodeType, DocumentSearchQuery
from ..state import AgentState, StateKey
from .base import ToolNode


class DocumentsRetriever(ToolNode[DocumentSearchQuery]):  # todo
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.DOC_RETRIEVER, DocumentSearchQuery, llm)

    async def _execute_tool(self, args: LegalSearchQuery) -> dict: ... # 벡터디비 유사도 기반 문서 검색

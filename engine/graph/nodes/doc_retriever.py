from typing import List
import requests
from pydantic import ValidationError
from langchain_core.language_models import BaseChatModel

from ..utils import AgentSpecLoader
from ..schema import LegalSearchQuery, NodeType, DocumentSearchQuery
from ..state import AgentState, StateKey
from .base import ToolNode


class DocumentsRetriever(ToolNode[DocumentSearchQuery]):  # todo
    def __init__(self, llm: BaseChatModel, version: str) -> None:
        super().__init__(NodeType.DOC_RETRIEVER, DocumentSearchQuery, llm, version)

    def _execute_tool(self, args: LegalSearchQuery) -> dict: ...

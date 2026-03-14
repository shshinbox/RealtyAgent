import re
import requests
from typing import Any
from langchain_core.language_models import BaseChatModel

from ..utils import AgentSpecLoader
from ..config import config_settings
from ..schema import LegalSearchQuery, NodeType
from .base import ToolNode
from ..logger import logger


class LegalRetriever(ToolNode[LegalSearchQuery]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.LEGAL_RETRIEVER, LegalSearchQuery, llm)
        self.base_url = AgentSpecLoader.load_elements(self.key, "base_url")

    def _doc_len(self, result: Any) -> int:
        """법령 API 응답 전용 파싱."""
        if not result or not isinstance(result, dict):
            return 0
        num = result.get("numOfRows")
        if num is None:
            num = result.get("Expc", {}).get("numOfRows")
        expc_list = None
        try:
            expc_list = result.get("Expc", {}).get("expc")
        except Exception:
            pass
        if isinstance(expc_list, list):
            return len(expc_list)
        if num is not None:
            try:
                return int(num)
            except Exception:
                m = re.search(r"(\d+)", str(num))
                return int(m.group(1)) if m else 0
        return 0

    async def _execute_tool(self, args: LegalSearchQuery) -> dict:

        logger.info(f"Executing LegalRetriever with args: {args}")

        api_params = {
            "OC": config_settings.KOREAN_LAW_OC,
            "target": "expc",
            "type": "JSON",
            "query": args.keyword,
            **args.model_dump(exclude={"keyword"}, exclude_none=True),
        }

        try:
            response = requests.get(self.base_url, params=api_params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.JSONDecodeError:
            # API 응답이 유효한 JSON이 아닌 경우
            logger.warning(
                f"Legal API returned invalid JSON. Response: {response.text[:100]}"
            )
            return {"documents": []}
        except requests.exceptions.RequestException as e:
            # 네트워크 에러, 타임아웃 등
            logger.error(f"Legal API request failed: {str(e)}")
            return {"documents": []}

from langchain_core.runnables import RunnableConfig

from ..schema import NodeType
from ..state import AgentState, StateKey
from .base import BaseNode
from ..logger import logger
from ..external_deps import ExternalDepsPort


class MemoryRetriever(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.MEMORY_RETRIEVER

    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {})
        external_fns: ExternalDepsPort = configurable.get("external_fns", {})
        search_memories_fn = external_fns.search_memories

        if not search_memories_fn:
            logger.error(f"[{self.key}] search_memories_fn is missing in config")

        # TODO: add vector generation logic
        try:
            search_memory = await search_memories_fn(
                query_vector=[],
                metadata_fields=["user_id"],
                metadata_values=[configurable.get("user_id")],
                top_k=5,
            )
            logger.info(
                f"[{self.key}] Memory search executed for user: {configurable.get('user_id')}"
            )
        except Exception as e:
            logger.error(f"[{self.key}] Failed to execute memory search: {e}")
            search_memory = ""

        return self._create_success_response(
            update_dict={
                StateKey.RETRIEVED_DOCS: {self.key: search_memory},
                StateKey.VERIFIER_TARGET_NODE: self.key,
            },
        )

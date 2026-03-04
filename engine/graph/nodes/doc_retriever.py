from langchain_core.runnables import RunnableConfig

from ..schema import NodeType
from .base import BaseNode
from ..logger import logger
from ..state import AgentState, StateKey, StateManager
from ..external_deps import ExternalDepsPort


class DocumentsRetriever(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.DOC_RETRIEVER)

    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {})
        external_fns: ExternalDepsPort = configurable.get("external_fns", {})
        search_docs_fn = external_fns.search_docs

        if not search_docs_fn:
            logger.error(f"[{self.key}] search_docs_fn is missing in config")

        try:
            sm: StateManager = StateManager(state=state)
            search_docs = await search_docs_fn(
                query=sm.refined_query,
                metadata_fields=["user_id"],
                metadata_values=[configurable.get("user_id")],
                top_k=5,
            )

            logger.info(
                f"[{self.key}] Document search executed for user: {configurable.get('user_id')}"
            )
        except Exception as e:
            logger.error(f"[{self.key}] Failed to execute document search: {e}")
            search_docs = []

        return self._create_success_response(
            update_dict={
                StateKey.RETRIEVED_DOCS: {self.key: search_docs},
                StateKey.VERIFIER_TARGET_NODE: self.key,
            },
        )

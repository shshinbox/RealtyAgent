from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import (
    NodeType,
    PlannerResponse,
)
from .base import LLMNode
from ..logger import logger


# node_stack 조합 → document_type 자동 보정 규칙
_STACK_TO_DOCTYPE: list[tuple[NodeType, str]] = [
    (NodeType.LEGAL_RETRIEVER, "legal_report"),
]


class Planner(LLMNode[PlannerResponse]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.PLANNER, PlannerResponse, llm)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)

        raw_query: str = sm.query
        feedback_content: str = sm.feedback

        prompt = self.prompt_template.format(
            raw_query=raw_query,
            human_feedback=feedback_content,
        )

        response: PlannerResponse = await self._ask_llm(prompt)

        logger.info(f"[Planner] LLM response received: response='{response}'")

        # LLM이 "chat"으로 내보낸 경우 planned_nodes 기반으로 보정
        # TODO: 향후 LLM이 적절한 document_type을 직접 반환하도록 개선하는 방안 검토
        doc_type = response.document_type
        if doc_type == "chat":
            for node, inferred_type in _STACK_TO_DOCTYPE:
                if node in response.planned_nodes:
                    doc_type = inferred_type
                    break

        return self._create_success_response(
            update_dict={
                StateKey.PLANNER_RESPONSE: response,
                StateKey.CONSULTATION_CONTEXT: {"document_type": doc_type},
            },
        )

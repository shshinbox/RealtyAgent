from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
import requests
from typing import Any

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse, EvaluationResponse
from .base import BaseNode
from ...security.guard import PromptGuard
from ...security.hallucination import HallucinationDetector
from ...security.privacy import PresidioKoreanEngine


class Evaluator(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.EVALUATOR

    async def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)

        guard_prompt: PromptGuard = PromptGuard()
        _is_secured: bool = await guard_prompt.is_secured(
            [AIMessage(content=sm.answer)]
        )

        hallucination_detector: HallucinationDetector = HallucinationDetector()
        _is_grounded: bool = await hallucination_detector.is_grounded(
            answer=sm.answer, context=sm.retrieved_docs
        )

        presidio: PresidioKoreanEngine = PresidioKoreanEngine()
        presidio_result: dict[str, Any] = await presidio.process(sm.answer)
        is_pii: bool = presidio_result.get("is_pii", False)
        masked_text: str = presidio_result.get("masked_text", sm.answer)

        # todo
        # evaluation_response: EvaluationResponse = EvaluationResponse(
        #     is_secured=_is_secured, is_grounded=_is_grounded, has_pii=is_pii
        # )

        # mock
        evaluation_response: EvaluationResponse = EvaluationResponse(
            is_secured=True, is_grounded=True, has_pii=False
        )

        return self._create_success_response(
            update_dict={
                StateKey.EVALUATION_RESPONSE: evaluation_response,
                StateKey.ANSWER: masked_text,
            },
        )

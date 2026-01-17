from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
import requests

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse, EvaluationResponse
from .base import BaseNode
from ..tools import GuardPrompt


class Evaluator(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.EVALUATOR

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)

        guard_prompt: GuardPrompt = GuardPrompt()

        is_secured_lakera: bool = guard_prompt.is_secured(
            [AIMessage(content=sm.answer)]
        )

        # todo
        evaluation_response: EvaluationResponse = EvaluationResponse(
            is_secured=is_secured_lakera, is_hallucination=False, is_include_pii=False
        )

        is_safe: bool = evaluation_response.is_safe()

        return self._create_success_response(
            update_dict={
                StateKey.EVALUATION_RESPONSE: evaluation_response,
            },
        )

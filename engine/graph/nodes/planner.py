from pydantic import ValidationError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage

from ..state import AgentState, StateKey, StateManager
from ..utils import AgentSpecLoader
from ..schema import (
    NodeType,
    HumanFeedback,
    PlannerResponse,
)
from .base import LLMNode


class Planner(LLMNode[PlannerResponse]):
    def __init__(self, llm: BaseChatModel, version: str) -> None:
        super().__init__(NodeType.PLANNER, PlannerResponse, llm, version)

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)

        raw_query: str = sm.query
        feedback_content: str = sm.feedback

        prompt = self.prompt_template.format(
            raw_query=raw_query,
            human_feedback=feedback_content,
        )

        response: PlannerResponse = self._ask_llm(prompt)

        print(response)

        return self._create_success_response(
            update_dict={
                StateKey.PLANNER_RESPONSE: response,
            },
        )

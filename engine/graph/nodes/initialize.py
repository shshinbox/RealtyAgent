from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
import requests

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse, EvaluationResponse
from .base import BaseNode
from ..utils import AgentSpecLoader
from ..tools import GuardPrompt
from ...error.errors import SecurityError


class Initializer(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.INITIALIZER
        self.system_prompt = AgentSpecLoader.load_elements(
            self.key, "system_prompt", "v1.0"
        )

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)

        raw_query: str = sm.query

        guard_prompt: GuardPrompt = GuardPrompt()

        if not guard_prompt.is_secured([HumanMessage(content=raw_query)]):
            raise SecurityError(node_name=self.key, context={StateKey.QUERY: raw_query})

        return self._create_success_response(
            messages=[
                SystemMessage(content=f"시스템 메시지: {self.system_prompt}"),
                HumanMessage(content=f"요청 메시지: {raw_query}"),
            ],
            update_dict={
                StateKey.QUERY: raw_query,
            },
        )

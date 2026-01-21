from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse, CircuitCheck
from .base import BaseNode


class Finalizer(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.FINALIZER

    async def _run(self, state: AgentState) -> dict:
        return self._create_success_response(
            update_dict={
                StateKey.ERRORS: None,
                StateKey.QUERY: None,
                StateKey.PLANNER_RESPONSE: None,
                StateKey.NEXT_NODE: None,
                StateKey.VERIFIER_TARGET_NODE: None,
                StateKey.CIRCUIT_CHECK: CircuitCheck.initialize(),
                StateKey.HUMAN_FEEDBACK: None,
                StateKey.IS_VERIFIED: None,
                StateKey.EVALUATION_RESPONSE: None,
                StateKey.RETRIEVED_DOCS: None,
                StateKey.API_ARGS: None,
            },
        )

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse
from .base import BaseNode


class Dispatcher(BaseNode):
    def __init__(self) -> None:
        self.key = NodeType.DISPATCHER

    async def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)
        planner_response: PlannerResponse = sm.planner_response

        if planner_response.is_exhausted():
            if not sm.answer:
                next_node: NodeType = NodeType.GENERATOR
            else:
                next_node: NodeType = NodeType.FINALIZER
        else:
            next_node: NodeType = planner_response.pop_stack()

        return self._create_success_response(
            update_dict={
                StateKey.NEXT_NODE: next_node,
                StateKey.PLANNER_RESPONSE: planner_response,
            },
        )

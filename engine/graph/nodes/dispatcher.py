from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, PlannerResponse
from .base import BaseNode
from ..logger import logger


class Dispatcher(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.DISPATCHER)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)
        planner_response: PlannerResponse = sm.planner_response

        logger.info(
            f"Dispatcher: planner_response.node_stack={planner_response.node_stack}"
        )

        if planner_response.is_exhausted():
            if not sm.answer:
                next_node: NodeType = NodeType.GENERATOR
            else:
                next_node: NodeType = NodeType.FINALIZER
        else:
            next_node: NodeType = planner_response.pop_stack()

        valid_next_nodes = {
            NodeType.LEGAL_RETRIEVER,
            NodeType.DOC_RETRIEVER,
            NodeType.MEMORY_RETRIEVER,
            NodeType.COUNSELOR,
            NodeType.GENERATOR,
            NodeType.HUMAN_REVIEWER,
            NodeType.FINALIZER,
        }

        if next_node not in valid_next_nodes:
            next_node = NodeType.GENERATOR

        update_dict = {
            StateKey.NEXT_NODE: next_node,
            StateKey.PLANNER_RESPONSE: planner_response,
        }

        return self._create_success_response(update_dict=update_dict)

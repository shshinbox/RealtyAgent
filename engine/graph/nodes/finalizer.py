from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from ..external_deps import ExternalDepsPort
from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, CircuitCheck
from .base import BaseNode
from ..logger import logger


class Finalizer(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.FINALIZER)

    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        configurable = config.get("configurable", {})
        external_fns: ExternalDepsPort = configurable.get("external_fns", {})
        push_task_fn = external_fns.push_task

        if not push_task_fn:
            logger.error(f"[{self.key}] push_task_fn is missing in config")

        sm: StateManager = StateManager(state=state)

        memory_data = {
            "user_id": configurable.get("user_id"),
            "thread_id": configurable.get("thread_id"),
            "refined_query": sm.refined_query,
            "final_answer": sm.answer,
        }

        try:
            await push_task_fn(queue_name="memory_queue", data=memory_data)
            logger.info(
                f"[{self.key}] Task pushed to Redis for user: {memory_data['user_id']}"
            )
        except Exception as e:
            logger.error(f"[{self.key}] Failed to push task to Redis: {e}")

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

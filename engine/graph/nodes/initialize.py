from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import (
    NodeType,
    CircuitCheck,
    HumanFeedback,
)
from .base import BaseNode
from ..utils import AgentSpecLoader
from ...security.guard import PromptGuard
from ..logger import logger


class Initializer(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.INITIALIZER)
        self.system_prompt = AgentSpecLoader.load_elements(
            self.key, "system_prompt", "v1.0"
        )

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)

        raw_query: str = sm.query

        promptguard: PromptGuard = PromptGuard()

        if not await promptguard.is_secured([HumanMessage(content=raw_query)]):
            logger.warning(f"Prompt Guard Alert: Potential prompt injection detected.")

        return self._create_success_response(
            messages=[
                SystemMessage(content=f"시스템 메시지: {self.system_prompt}"),
                HumanMessage(content=f"요청 메시지: {raw_query}"),
            ],
            update_dict={
                StateKey.QUERY: raw_query,
                StateKey.ANSWER: "",
                StateKey.RETRIEVED_DOCS: {},
                StateKey.API_ARGS: {},
                StateKey.CIRCUIT_CHECK: CircuitCheck.initialize(),
                StateKey.HUMAN_FEEDBACK: HumanFeedback(content="", human_action=None),
                StateKey.RETRY_COUNT: 0,
            },
        )

from typing import AsyncGenerator, Optional, Callable, Any, Dict
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

from .state import StateKey, HumanFeedback
from .schema import NodeType
from .workflow import build_workflow


class GraphEngine:
    def __init__(
        self, llm_map: Dict[NodeType, BaseChatModel], checkpointer: BaseCheckpointSaver
    ):
        self._workflow = build_workflow(llm_map=llm_map)
        self._app = self._workflow.compile(
            checkpointer=checkpointer, interrupt_before=[NodeType.HUMAN_REVIEWER]
        )

    async def run(
        self,
        user_id: str,
        thread_id: str,
        query: str,
        external_fns: Optional[Dict[str, Callable]] = None,
    ) -> AsyncGenerator:
        config = self._build_config(user_id, thread_id, external_fns)
        input_data = {StateKey.QUERY: query}

        async for event in self._app.astream_events(input_data, config, version="v2"):
            yield event

    async def resume(
        self,
        user_id: str,
        thread_id: str,
        feedback: str,
        external_fns: Optional[Dict[str, Callable]] = None,
    ) -> AsyncGenerator:
        config = self._build_config(user_id, thread_id, external_fns)

        await self._app.aupdate_state(
            config,
            {
                StateKey.HUMAN_FEEDBACK: HumanFeedback(
                    content=feedback, human_action=None
                )
            },
        )

        async for event in self._app.astream_events(None, config, version="v2"):
            yield event

    async def aget_state(self, user_id: str, thread_id: str):
        config = self._build_config(user_id, thread_id)
        state = await self._app.aget_state(config)
        return state

    def _build_config(
        self,
        user_id: str,
        thread_id: str,
        external_fns: Optional[Dict[str, Callable]] = None,
    ) -> RunnableConfig:
        checkpoint_id = f"{user_id}:{thread_id}"

        config: RunnableConfig = {"configurable": {"thread_id": checkpoint_id}}

        if external_fns:
            config["configurable"].update(external_fns)

        return config

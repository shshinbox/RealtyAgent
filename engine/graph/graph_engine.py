from typing import AsyncGenerator, Optional, cast

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from .state import StateKey, HumanFeedback, AgentState
from .schema import NodeType
from .workflow import build_workflow


class GraphEngine:
    def __init__(self, llm: BaseChatModel, checkpointer: AsyncSqliteSaver):
        self._workflow = build_workflow(llm=llm)
        self._app = self._workflow.compile(
            checkpointer=checkpointer, interrupt_before=[NodeType.HUMAN_REVIEWER]
        )

    async def run(
        self,
        user_id: str,
        thread_id: str,
        query: str,
    ) -> AsyncGenerator:
        """
        신규 대화를 시작하거나 기존 대화에 이어 질문한다.
        thread_id가 같으면 Redis에서 이전 대화 기록을 자동으로 불러온다.

        Args:
            thread_id: 대화 구분을 위한 세션 ID
            query: 사용자 질문

        Returns: 랭그래프 내부에서 발생하는 이벤트 스트림
            - on_chat_model_stream: LLM 토큰 단위 출력
            - on_chain_start/end: 노드 실행 상태 변화
            - on_tool_start/end: 도구 호출 정보 등
        """

        config: RunnableConfig = self._configurable(
            user_id=user_id, thread_id=thread_id
        )
        input_data = {StateKey.QUERY: query}

        async for event in self._app.astream_events(input_data, config, version="v2"):
            yield event

    async def resume(
        self, user_id: str, thread_id: str, feedback: str
    ) -> AsyncGenerator:
        """
        인터럽트되어 멈춘 지점부터 재개한다.
        """
        config: RunnableConfig = self._configurable(
            user_id=user_id, thread_id=thread_id
        )

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

    async def get_state(self, user_id: str, thread_id: str) -> Optional[AgentState]:
        """
        현재 워크플로우의 상태를 확인한다.
        """
        config: RunnableConfig = self._configurable(
            user_id=user_id, thread_id=thread_id
        )
        snapshot = await self._app.aget_state(config)

        if not snapshot or not snapshot.values:
            return None
        
        return cast(AgentState, snapshot.values)

    def _configurable(self, user_id: str, thread_id: str) -> RunnableConfig:
        checkpoint_id: str = self._checkpoint_id(user_id, thread_id)
        return {"configurable": {"thread_id": checkpoint_id}}

    def _checkpoint_id(self, user_id: str, thread_id: str) -> str:
        return f"{user_id}:{thread_id}"

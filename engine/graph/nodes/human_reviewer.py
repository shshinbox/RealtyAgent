from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, HumanFeedback, HumanFeedbackResponse
from .base import LLMNode
from ...security.guard import PromptGuard
from ..logger import logger


class HumanReviewer(LLMNode[HumanFeedbackResponse]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.HUMAN_REVIEWER, HumanFeedbackResponse, llm)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)

        # user_input: resume()이 주입한 단일 입력 채널
        feedback_content: str = sm.user_input

        guard_prompt: PromptGuard = PromptGuard()

        if not await guard_prompt.is_secured([HumanMessage(content=feedback_content)]):
            logger.warning(f"Prompt Guard Alert: Potential prompt injection detected.")

        prompt: str = self.prompt_template.format(feedback=feedback_content)

        response: HumanFeedbackResponse = await self._ask_llm(prompt)

        # 내부에서 HumanFeedback 객체 생성 후 action 설정
        human_feedback: HumanFeedback = HumanFeedback(
            content=feedback_content, human_action=response.action
        )

        return self._create_success_response(
            messages=[HumanMessage(content=f"사용자 피드백: {human_feedback}")],
            update_dict={
                StateKey.HUMAN_FEEDBACK: human_feedback,
                StateKey.USER_INPUT: None,  # 처리 완료된 입력 초기화
            },
        )

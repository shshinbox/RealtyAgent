from typing import Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, HumanFeedback, HumanAction, HumanFeedbackResponse
from ..utils import AgentSpecLoader
from .base import LLMNode
from ..tools import GuardPrompt
from ...error.errors import SecurityError


class HumanReviewer(LLMNode[HumanFeedbackResponse]):
    def __init__(self, llm: BaseChatModel, version: str) -> None:
        super().__init__(NodeType.HUMAN_REVIEWER, HumanFeedbackResponse, llm, version)

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)
        human_feedback: HumanFeedback = sm.human_feedback
        feedback_content: str = sm.feedback

        guard_prompt: GuardPrompt = GuardPrompt()

        if not guard_prompt.is_secured([HumanMessage(content=feedback_content)]):
            raise SecurityError(
                node_name=self.key, context={StateKey.HUMAN_FEEDBACK: human_feedback}
            )

        prompt: str = self.prompt_template.format(feedback=feedback_content)

        response: HumanFeedbackResponse = self._ask_llm(prompt)

        human_feedback.set_human_action(response.action)

        return self._create_success_response(
            messages=[HumanMessage(content=f"사용자 피드백: {human_feedback}")],
            update_dict={StateKey.HUMAN_FEEDBACK: human_feedback},
        )

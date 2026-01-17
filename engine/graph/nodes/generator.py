from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage
from langchain_core.messages import trim_messages

from .base import LLMNode
from ..state import AgentState, StateKey, StateManager
from ..schema import (
    NodeType,
    PlannerResponse,
    EvaluationResponse,
    GeneratorResponse,
)


class Generator(LLMNode[GeneratorResponse]):
    def __init__(self, llm: BaseChatModel, version: str) -> None:
        super().__init__(NodeType.GENERATOR, GeneratorResponse, llm, version)

    def _run(self, state: AgentState) -> dict:
        sm: StateManager = StateManager(state=state)

        trimmed_msgs = trim_messages(
            sm.messages,
            strategy="last",
            token_counter=self.char_counter,
            max_tokens=2000,
            start_on="human",
            include_system=True,
        )

        refined_query: str = sm.refined_query or ""
        feedback: str = sm.feedback or ""

        prompt: str = self.prompt_template.format(
            history=trimmed_msgs,
            retrieved_docs=sm.retrieved_docs,
            refined_query=refined_query,
            feedback=feedback,
        )

        response: GeneratorResponse = self._ask_llm(prompt)

        return self._create_success_response(
            messages=[AIMessage(content=f"답변: {response.answer}")],
            update_dict={StateKey.ANSWER: response.answer},
        )

    def char_counter(self, messages: list[BaseMessage]) -> int:
        return sum(len(m.content) for m in messages)

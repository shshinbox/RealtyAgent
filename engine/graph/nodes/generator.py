from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage
from langchain_core.messages import trim_messages
from langchain_core.runnables import RunnableConfig

from .base import LLMNode
from ..state import AgentState, StateKey, StateManager
from ..schema import (
    NodeType,
    GeneratorResponse,
    ConsultationContext,
)
from ..utils import AgentSpecLoader
from ..logger import logger

DEFAULT_DOCUMENT_TYPE = "chat"


class Generator(LLMNode[GeneratorResponse]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.GENERATOR, GeneratorResponse, llm)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
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
        ctx: ConsultationContext = sm.consultation_context

        document_type: str = ctx.document_type or DEFAULT_DOCUMENT_TYPE

        try:
            prompt_template: str = AgentSpecLoader.load_prompt_by_document_type(document_type)
        except (FileNotFoundError, ValueError):
            logger.warning(
                f"[Generator] Template not found for document_type='{document_type}'. "
                f"Falling back to '{DEFAULT_DOCUMENT_TYPE}'."
            )
            prompt_template = AgentSpecLoader.load_prompt_by_document_type(DEFAULT_DOCUMENT_TYPE)

        format_kwargs = dict(
            history=trimmed_msgs,
            retrieved_docs=sm.retrieved_docs,
            refined_query=refined_query,
            feedback=feedback,
            consultation_context=ctx.model_dump(),
        )
        # chat 템플릿은 consultation_context 변수가 없으므로 안전하게 format
        try:
            prompt: str = prompt_template.format(**format_kwargs)
        except KeyError:
            prompt: str = prompt_template.format(
                history=trimmed_msgs,
                retrieved_docs=sm.retrieved_docs,
                refined_query=refined_query,
                feedback=feedback,
            )

        response: GeneratorResponse = await self._ask_llm(prompt)

        return self._create_success_response(
            messages=[AIMessage(content=f"답변: {response.answer}")],
            update_dict={StateKey.ANSWER: response.answer},
        )

    def char_counter(self, messages: list[BaseMessage]) -> int:
        return sum(len(m.content) for m in messages)

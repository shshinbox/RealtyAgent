from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, CounselorResponse, ConsultationContext
from .base import LLMNode
from ...security.guard import PromptGuard
from ..logger import logger


class Counselor(LLMNode[CounselorResponse]):
    def __init__(self, llm: BaseChatModel) -> None:
        super().__init__(NodeType.COUNSELOR, CounselorResponse, llm)

    async def _run(self, state: AgentState, _config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)
        ctx: ConsultationContext = sm.consultation_context
        user_response: str = sm.user_input  # 단일 입력 채널, cold-start 시 빈 문자열

        # resume 이후(유저 답변이 있을 때)만 보안 검사
        if user_response:
            guard_prompt: PromptGuard = PromptGuard()
            if not await guard_prompt.is_secured([HumanMessage(content=user_response)]):
                logger.warning(
                    "Prompt Guard Alert: Potential prompt injection in counselor."
                )

        prompt: str = self.prompt_template.format(
            query=sm.query,
            consultation_context=ctx,
            user_response=user_response,
        )

        response: CounselorResponse = await self._ask_llm(prompt)

        # 기존 context에 이번 턴 수집 정보 누적 (동일 키는 새 값으로 덮어씀)
        collected_info = {f.key: f.value for f in response.collected_fields}
        existing = {
            k: v
            for k, v in ctx.model_dump().items()
            if k not in ("document_type", "is_ready")
        }
        updated_context = ConsultationContext(
            document_type=response.document_type,
            is_ready=response.is_ready,
            **{**existing, **collected_info},
        )

        update_dict = {
            StateKey.CONSULTATION_CONTEXT: updated_context.model_dump(),
            StateKey.USER_INPUT: None,  # 처리 완료된 입력 초기화
        }

        if response.is_ready:
            # 수집 완료: 질문 채널 비워서 프론트가 자동 resume 하도록 유도
            update_dict[StateKey.COUNSELOR_QUESTION] = None
            logger.info(
                f"[Counselor] Ready to generate. document_type={response.document_type}"
            )
        else:
            # 다음 질문을 counselor_question 채널에 담아 프론트에 전달
            update_dict[StateKey.COUNSELOR_QUESTION] = response.question
            logger.info(f"[Counselor] Asking: {response.question}")

        return self._create_success_response(
            messages=(
                [AIMessage(content=f"[상담] {response.question}")]
                if not response.is_ready
                else []
            ),
            update_dict=update_dict,
        )

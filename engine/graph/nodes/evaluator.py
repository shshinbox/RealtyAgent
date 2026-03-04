from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from typing import Any

from ..state import AgentState, StateKey, StateManager
from ..schema import NodeType, EvaluationResponse
from .base import BaseNode
from ...security.guard import PromptGuard
from ...security.hallucination import HallucinationDetector
from ...security.privacy import PresidioKoreanEngine


class Evaluator(BaseNode):
    def __init__(self) -> None:
        super().__init__(NodeType.EVALUATOR)

    async def _run(self, state: AgentState, config: RunnableConfig) -> dict:
        sm: StateManager = StateManager(state=state)
        retry_count: int = sm.retry_count or 0

        # # 1. Safety 검증 (Prompt Guard) # TODO
        # guard_prompt: PromptGuard = PromptGuard()
        # _is_secured: bool = await guard_prompt.is_secured(
        #     [AIMessage(content=sm.answer)]
        # )

        # # 2. Hallucination 감지
        # hallucination_detector: HallucinationDetector = HallucinationDetector()
        # _is_grounded: bool = await hallucination_detector.is_grounded(
        #     answer=sm.answer, context=sm.retrieved_docs
        # )

        # # 3. PII 마스킹
        # presidio: PresidioKoreanEngine = PresidioKoreanEngine()
        # presidio_result: dict[str, Any] = await presidio.process(sm.answer)
        # is_pii: bool = presidio_result.get("is_pii", False)
        # masked_text: str = presidio_result.get("masked_text", sm.answer)

        # 4. 평가 결과 생성 # TODO: 이후 실제값 입력 필요
        evaluation_response: EvaluationResponse = EvaluationResponse(
            is_secured=True, is_grounded=True, has_pii=False
        )

        # 5. 검증 결과에 따른 라우팅 결정
        update_dict = {
            StateKey.EVALUATION_RESPONSE: evaluation_response,
            StateKey.ANSWER: sm.answer,  # TODO: 이후 masked_text, 교체
        }

        # 검증 실패 시 재시도 로직
        _is_secured = True  # TODO: 이후 삭제 라인
        _is_grounded = True  # TODO: 이후 삭제 라인

        if not _is_secured:
            # 보안 위반: 즉시 Human Reviewer로
            return self._create_success_response(
                update_dict={**update_dict, StateKey.NEXT_NODE: NodeType.HUMAN_REVIEWER}
            )

        if not _is_grounded and retry_count < 3:
            # Hallucination 감지: 자동 재생성 (최대 3회)
            return self._create_success_response(
                update_dict={
                    **update_dict,
                    StateKey.NEXT_NODE: NodeType.GENERATOR,
                    StateKey.RETRY_COUNT: retry_count + 1,
                }
            )

        if not _is_grounded and retry_count >= 3:
            # 3회 재시도 초과: Human Reviewer로
            return self._create_success_response(
                update_dict={
                    **update_dict,
                    StateKey.NEXT_NODE: NodeType.HUMAN_REVIEWER,
                    StateKey.RETRY_COUNT: retry_count,
                }
            )

        # 모든 검증 통과: 다음 단계로
        return self._create_success_response(
            update_dict={**update_dict, StateKey.NEXT_NODE: None}
        )

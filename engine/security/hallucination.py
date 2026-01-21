import json
from typing import List, Union, Any
from openai import OpenAI

from ..graph.logger import logger
from ..graph.config import config_settings


class HallucinationDetector:
    def __init__(self):
        self.BASE_URL = "https://api.upstage.ai/v1"

    async def is_grounded(self, context: Union[str, list, dict], answer: str) -> bool:
        try:
            result: str = await self._check_groundedness(context=context, answer=answer)
            return result != "not_grounded"
        except Exception as e:
            logger.warning(f"HallucinationDetector failed. error: {str(e)}")
            return False

    async def _check_groundedness(
        self, context: Union[str, list, dict], answer: str
    ) -> str:
        """
        Upstage Groundedness Check API를 호출하여 생성된 답변의 근거성(Hallucination 여부)을 검증합니다.

        이 함수는 제공된 컨텍스트(참조 문서/데이터)와 생성된 답변 사이의 논리적 함의 관계를 분석합니다.
        내부적으로 Solar-10.7B 기반의 NLI(Natural Language Inference) 특화 모델을 사용하여
        답변이 근거에 기반했는지(Grounded) 아니면 허구인지(Not Grounded)를 판별합니다.

        Args:
            context (Union[str, list, dict]): 답변의 근거가 되는 정보입니다.
                - str: 텍스트 그대로 처리
                - list: 리스트 내 요소들을 줄바꿈(\n)으로 병합하여 처리
                - dict: JSON 형태(indent=2)로 직렬화하여 처리
            answer (str): 검증 대상이 되는 생성된 답변 문장입니다.

        Returns:
            str: 검증 결과 레이블 (다음 3가지 중 하나를 반환)
                - 'grounded': 답변이 근거 문서와 논리적으로 일치함 (정상)
                - 'not_grounded': 답변 중에 근거 문서에 없는 내용이나 모순이 포함됨 (할루시네이션)
                - 'not_sure': 근거가 부족하거나 모델이 확신할 수 없음
        """
        client = OpenAI(
            api_key=config_settings.UPSTAGE_API_KEY,
            base_url=self.BASE_URL,
        )

        serialize_context: str = self._serialize_context(context)

        response = client.chat.completions.create(
            model="groundedness-check-240502",
            messages=[
                {
                    "role": "user",
                    "content": serialize_context,
                },
                {"role": "assistant", "content": answer},
            ],
        )

        return response.choices[0].message.content or ""

    def _serialize_context(self, context: Union[str, List[Any], dict[Any, Any]]) -> str:
        if isinstance(context, str):
            return context

        elif isinstance(context, list):
            return "\n".join(str(item) for item in context)

        elif isinstance(context, dict):
            return json.dumps(context, ensure_ascii=False, indent=2)

        return str(context)

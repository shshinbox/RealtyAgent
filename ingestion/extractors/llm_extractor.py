from llama_index.core.llms import LLM
from llama_index.core.indices.property_graph import SimpleLLMPathExtractor


def build_llm_extractor(llm: LLM) -> SimpleLLMPathExtractor:
    """
    LLM 기반 개체/관계 추출기.
    텍스트 문맥을 이해하여 자유로운 형태의 (주체, 관계, 대상) 트리플을 추출합니다.

    예시 추출 결과:
      - (은마아파트, 위치, 강남구 대치동)
      - (주택법 제49조, 규정, 분양가 상한제)
      - (강남구, 포함, 서울특별시)
    """
    return SimpleLLMPathExtractor(
        llm=llm,
        max_paths_per_chunk=10,
        num_workers=4,
    )

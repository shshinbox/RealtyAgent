import os
from typing import cast
import logging
from langchain_openai import ChatOpenAI
from engine import (
    GraphEngine,
    NodeType,
    HumanFeedback,
    SecurityError,
    StateManager,
    StateKey,
    AgentState,
)
from pydantic import SecretStr


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def simple_test():
    llm = ChatOpenAI(
        model="gpt-4o", api_key=SecretStr(OPENAI_API_KEY or ""), temperature=0
    )

    try:
        engine = GraphEngine(llm=llm, version="v1.0")
        logger.info("GraphEngine이 성공적으로 빌드되었습니다.")
    except Exception as e:
        logger.error(f"엔진 빌드 실패: {e}")
        return

    test_thread_id = "test_user_001"
    test_query = "강남구 전세 사기 관련 법률 판례를 찾아줘."

    logger.info("\n" + "=" * 50)
    logger.info(f"테스트 시작 | Query: {test_query}")
    logger.info("=" * 50)

    try:
        final_state: AgentState = cast(
            AgentState, engine.run(thread_id=test_thread_id, query=test_query)
        )
        sm: StateManager = StateManager(state=final_state)

        logger.info("\n[최종 실행 결과]")
        logger.info(f"상태: SUCCESS")
        logger.info(f"답변: {sm.answer}")

    except SecurityError as e:
        logger.error("\n[보안 차단]")
        logger.error(f"사유: {e.message}")
        logger.error(f"노드: {e.node_name}")

    except Exception as e:
        logger.error(f"\n[시스템 에러 발생]: {e}")


if __name__ == "__main__":
    simple_test()

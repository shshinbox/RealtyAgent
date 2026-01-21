import os
import asyncio
import logging
from pydantic import SecretStr
import aiosqlite

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from engine import GraphEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def clean_up_db(db_path: str = "checkpoints.db"):
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
            print(f"[Test-Setup] 기존 DB({db_path}) 삭제 완료.")
        except Exception as e:
            print(f"[Error] 삭제 중 오류 발생: {e}")


async def get_user_input(prompt: str) -> str:
    """비동기 환경에서 사용자 입력을 받기 위한 헬퍼"""
    return await asyncio.to_thread(input, prompt)


async def run_test():
    clean_up_db()

    async with aiosqlite.connect("checkpoints.db") as conn:
        checkpointer = AsyncSqliteSaver(conn)
        await checkpointer.setup()

        llm = ChatOpenAI(
            model="gpt-4o", api_key=SecretStr(OPENAI_API_KEY), temperature=0
        )
        engine = GraphEngine(llm=llm, checkpointer=checkpointer)

        test_user_id = "user001"
        test_thread_id = "test_session"
        test_query = "전세 사기 관련 법률 판례를 찾고 초안을 작성해줘. 단계별로 내 확인을 받아야 해."

        print(f"\n{'='*20} [시작] 그래프 실행 {'='*20}")

        # 1. 초기 실행
        async for event in engine.run(
            user_id=test_user_id, thread_id=test_thread_id, query=test_query
        ):
            handle_event(event)

        # 2. 범용 인터럽트 핸들링 루프
        # state.next에 값이 있다는 것은 interrupt_before/after에 의해 멈췄음을 의미함
        while True:
            state = await engine.get_state(
                user_id=test_user_id, thread_id=test_thread_id
            )

            if not state.next:
                print(f"\n{'='*20} [종료] 모든 노드 실행 완료 {'='*20}")
                break

            # 현재 대기 중인 노드 정보 추출
            waiting_node = state.next[0]
            print(f"\n\n[휴먼 인터럽트]: '{waiting_node}' 노드에서 승인이 필요합니다.")

            print(f"중간결과물: {state.values.get('answer', '결과 없음')}")

            # 사용자로부터 피드백 입력 받음 (범용적 입력)
            user_feedback = await get_user_input(
                f"[{waiting_node}] 피드백을 입력하세요 (엔터 시 기본 진행): "
            )

            if not user_feedback.strip():
                user_feedback = "확인했습니다. 계속 진행하세요."

            print(f"\n{'='*20} [재개] '{waiting_node}' 이후 흐름 실행 {'='*20}")

            # 피드백을 주입하며 다시 실행
            async for event in engine.resume(
                user_id=test_user_id, thread_id=test_thread_id, feedback=user_feedback
            ):
                handle_event(event)

        # 3. 결과 검증
        final_state = await engine.get_state(
            user_id=test_user_id,
            thread_id=test_thread_id,
        )
        print(f"\n\n{'='*20} [최종 결과 리포트] {'='*20}")
        print(f"최종 답변: {final_state.values.get('answer', '결과 없음')}")
        print(f"메시지 개수: {len(final_state.values.get('messages', []))}개")


def handle_event(event):
    """그래프 스트리밍 이벤트를 출력하는 공통 로직"""
    kind = event.get("event")
    if kind == "on_chat_model_stream":
        content = event["data"]["chunk"].content
        if content:
            print(content, end="", flush=True)
    elif kind == "on_chain_start" and "node" in event.get("metadata", {}):
        node_name = event["metadata"]["node"]
        if not node_name.startswith("__"):
            print(f"\n\n[현재 실행 노드]: {node_name}")


if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n테스트가 사용자에 의해 중단되었습니다.")

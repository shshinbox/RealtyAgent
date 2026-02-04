# RealtyAgent - API Gateway

## 📌 개요

LangGraph 기반의 멀티 노드 에이전트 오케스트레이션을 위한 FastAPI 게이트웨이입니다.

## 🛠️ 적용 기술
- **Framework**: FastAPI
- **Orchestration**: LangGraph (GraphEngine)
- **LLMs**: -
- **Storage/State**: 
  - **Checkpointer**: -
  - **Vector DB**: Qdrant
  - **Relational DB**: PostgreSQL 
  - **Message Queue**: Redis 


## 📡 주요 기능
- **Lifespan Management**: 앱 기동 시 LLM 맵 초기화, DB 커넥션 풀링 및 LangGraph 엔진 인스턴스화 수행
- **Dependency Injection**: `_external_deps`를 통해 그래프 노드에서 사용할 외부 함수(Persona 조회, Redis 태스크 전송)를 주입
- **Streaming**: 모든 채팅 엔드포인트는 `StreamingResponse`(SSE)를 통해 실시간 토큰 전송
  

## 🧬 API Endpoints

### Chat Operations
| Method | Endpoint                   | Description                                     |
| :----- | :------------------------- | :---------------------------------------------- |
| `POST` | `/chat`                    | 신규 대화 세션 시작 (thread_id 생성)            |
| `POST` | `/chat/{thread_id}`        | 기존 세션에 추가 쿼리 실행                      |
| `POST` | `/chat/{thread_id}/resume` | Interrupt(HITL) 이후 사용자 피드백 반영 및 재개 |
| `GET`  | `/chat/{thread_id}/state`  | 현재 그래프 세션의 상태(Snapshot) 조회          |


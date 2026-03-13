# 시스템 개요

## 프로젝트 소개

**RealtyAgent**는 부동산 및 법률 상담에 특화된 멀티에이전트 AI 시스템입니다.
사용자의 질문 의도를 분석하고, 관련 문서 및 법적 근거를 검색하여 구조화된 상담 리포트를 생성합니다.

기존 선형(Linear) 워크플로우의 한계를 극복하기 위해 **LangGraph** 기반으로 설계되었으며,
에이전트 노드 간 상태(State)를 공유하는 그래프 구조로 유연한 실행 경로를 지원합니다.

---

## 시스템 구성

```
┌─────────────────────────────────────────────────────┐
│                    Client / UI                      │
└────────────────────────┬────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────┐
│              FastAPI Gateway (server/)              │
│         - 사용자 요청 수신 및 응답 반환                 │
│         - 인증, 세션, 렌더링 처리                      │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│           LangGraph Engine (engine/)                │
│         - 멀티에이전트 워크플로우 실행                  │
│         - 노드 간 상태 관리                           │
└──────┬────────────────┬──────────────────┬──────────┘
       │                │                  │
┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼────────┐
│ PostgreSQL  │  │  Qdrant     │  │     Redis      │
│ 대화 이력    │  │  Vector DB  │  │  Queue / Cache │
│ 사용자 프로필 │  │  공문서 RAG  │  │                │
└─────────────┘  └─────────────┘  └────────────────┘
                                          │
                              ┌───────────▼───────────┐
                              │   Worker (worker/)    │
                              │  GLiNER 엔티티 추출     │
                              └───────────────────────┘
```

---

## 에이전트 워크플로우

사용자의 질문은 아래 노드 파이프라인을 통해 처리됩니다.

```
Initializer → Planner → Dispatcher
                             │
             ┌───────────────┼───────────────────┐
             │               │                   │
      LegalRetriever   DocRetriever       MemoryRetriever
             │               │                   │
             └───────────────┼───────────────────┘
                             │
                          Verifier
                             │
                         Dispatcher (재라우팅)
                             │
                         Generator
                             │
                         Evaluator
                             │
                    ┌────────┴────────┐
                    │                 │
             HumanReviewer       Finalizer → END
```

### 노드 역할

| 노드 | 역할 |
|---|---|
| **Initializer** | 세션 초기화, 대화 이력 로딩 |
| **Planner** | 사용자 의도 분석 후 실행 노드 순서(node_stack) 계획 |
| **Dispatcher** | node_stack 기반으로 다음 실행 노드 라우팅 |
| **LegalRetriever** | 판례, 법령 등 법적 근거 검색 |
| **DocRetriever** | 매물, 실거래가, 공문서 등 사실 관계 검색 |
| **MemoryRetriever** | 과거 대화 및 사용자 맥락 조회 |
| **Verifier** | 검색 결과 유효성 검증, 추가 검색 여부 판단 |
| **Generator** | 검색 결과 기반 구조화된 리포트 데이터 생성 |
| **Evaluator** | 생성 결과 품질 평가, 재생성 또는 검토 요청 판단 |
| **HumanReviewer** | 사용자 확인이 필요한 경우 중간 승인 요청 |
| **Finalizer** | 최종 결과 정리 및 후처리 작업(Worker 태스크 발행) |

---

## 출력 형식

**Generator**는 구조화된 JSON 형태로 리포트 데이터를 생성하며, 이후 **Jinja2 렌더러**를 통해 HTML 및 PDF로 변환됩니다.

```json
{
  "report_meta": { "title": "...", "summary": "..." },
  "key_issues": [...],
  "legal_grounds": [...],
  "practical_advice": [...],
  "precautions": [...]
}
```

---

## ExternalDepsPort 인터페이스 설계

`engine/`(LangGraph)은 저장소와 외부 서비스를 직접 호출하지 않습니다.
`ExternalDepsPort` Protocol을 통해 의존성을 주입받으며, 구체적인 구현은 `server/`가 담당합니다.

```
engine/ (LangGraph 노드)
  └─ ExternalDepsPort (Protocol 인터페이스)
       ↑ 구현체 주입
server/service/external_deps_service.py (ExternalDeps)
  ├─ search_memories()  → Qdrant [user_memory]
  ├─ search_docs()      → ingestion/ (LlamaIndex 기반, 하이브리드 검색)
  ├─ get_user_persona() → PostgreSQL
  └─ push_task()        → Redis Queue
```

이 구조로 인해 `engine/`은 LlamaIndex, Qdrant, PostgreSQL 등 구체적인 구현을 전혀 알지 못합니다.
검색 전략을 변경하거나 저장소를 교체해도 `engine/` 코드는 수정할 필요가 없습니다.

**인터페이스 정의 위치:** [engine/graph/external_deps.py](../../engine/graph/external_deps.py)

---

## 저장소 구성

저장소 상세 설계는 [storage-strategy.md](./storage-strategy.md)를 참고합니다.

| 저장소 | 용도 |
|---|---|
| **PostgreSQL** | 대화 이력 (시간순), 사용자 프로필 (GLiNER 엔티티) |
| **Qdrant (Vector DB)** | 공문서 RAG 검색, 사용자 메모리 검색 |
| **Redis** | Worker 태스크 큐, 캐시 |
| **Neo4j (예정)** | 공문서 개체 간 관계망 (GraphRAG) |

---

## 주요 기술 스택

| 구분 | 기술 |
|---|---|
| 에이전트 프레임워크 | LangGraph |
| API 서버 | FastAPI |
| 엔티티 추출 | GLiNER (DeBERTa-v3 기반) |
| Vector DB | Qdrant |
| 관계형 DB | PostgreSQL |
| 메시지 큐 | Redis |
| 리포트 렌더링 | Jinja2 (HTML / PDF) |
| 문서 수집 파이프라인 | LlamaIndex (ingestion/ 패키지, 예정) |

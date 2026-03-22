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
             ┌───────────────┼──────────────────────┐
             │               │                      │
          Counselor   LegalRetriever (루프)   DocRetriever (루프)
          (루프)             │               MemoryRetriever
             │               └──────────────────────┘
             │                          │
             └──────────── Dispatcher (재라우팅)
                                        │
                                    Generator
                                        │
                                    Evaluator
                                        │
                             ┌──────────┴──────────┐
                             │                     │
                      HumanReviewer           Finalizer → END
```

### 노드 역할

| 노드 | 역할 |
|---|---|
| **Initializer** | 세션 초기화, 대화 이력 로딩 |
| **Planner** | 사용자 의도 분석 후 실행 노드 순서(node_stack) 계획 |
| **Dispatcher** | node_stack 기반으로 다음 실행 노드 라우팅 |
| **Counselor** | 문서 작성 전 정보 수집 상담. interrupt_after로 동작하며 필요 정보가 모일 때까지 루프 |
| **LegalRetriever** | 판례, 법령 등 법적 근거 검색. 검증 실패 시 self-loop (circuit breaker 3회) |
| **DocRetriever** | 매물, 실거래가, 공문서 등 사실 관계 검색. 동일한 self-loop 구조 |
| **MemoryRetriever** | 과거 대화 및 사용자 맥락 조회. 항상 Dispatcher로 복귀 |
| **Generator** | 문서 유형별 YAML 템플릿을 동적 로딩하여 결과물 생성 |
| **Evaluator** | 생성 결과 품질 평가, 재생성 또는 검토 요청 판단 |
| **HumanReviewer** | interrupt_before로 동작하며 사용자 승인 후 분기 처리 |
| **Finalizer** | 최종 결과 정리 및 후처리 작업(Worker 태스크 발행) |

---

## 출력 형식

**Generator**는 `ConsultationContext.document_type`에 따라 문서 유형별 YAML 프롬프트 템플릿을 동적으로 로딩하여 결과물을 생성합니다.

| 문서 유형 | 설명 |
|---|---|
| `chat` | 가벼운 대화형 응답 (기본값, Counselor 없이 바로 응답) |
| `legal_report` | 법률 상담 리포트 (쟁점 분석, 법적 근거, 실무 조언) |
| `lease_contract` | 임대차 계약서 |
| `sale_contract` | 부동산 매매 계약서 |
| `legal_memo` | 내용증명 / 법률 메모 |

문서 유형이 `chat`이 아닌 경우, Planner는 `counselor`를 `generator` 앞에 배치하여 사용자로부터 필요한 정보를 먼저 수집합니다.

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
| **Neo4j** | 공문서 개체 간 관계망 (GraphRAG) |

---

## 서버 초기화 구조

`main.py`는 순서 조율만 담당하며, 각 인프라의 초기화 책임은 `server/bootstrap/`에 분리되어 있습니다.

```
server/bootstrap/
  settings.py    APP_ENV 기반 .env 파일 로딩
  llm.py         NodeType → ChatOpenAI 모델 매핑
  storage.py     Redis / PostgreSQL / Qdrant(QdrantSearcher) / Neo4j 초기화 및 종료
  engine.py      SQLite checkpointer + GraphEngine 조합
  ingestion.py   LLM·EmbedModel 생성 후 DocumentPipeline + DocumentRetriever 조합
```

---

## 주요 기술 스택

| 구분 | 기술 |
|---|---|
| 에이전트 프레임워크 | LangGraph |
| API 서버 | FastAPI |
| 프론트엔드 | Vanilla HTML / CSS / JS (SPA, 프레임워크 없음) |
| 엔티티 추출 | GLiNER (DeBERTa-v3 기반) |
| Vector DB | Qdrant |
| 관계형 DB | PostgreSQL |
| 메시지 큐 | Redis |
| 리포트 렌더링 | Jinja2 (HTML 패널 스니펫) |
| 문서 수집 파이프라인 | LlamaIndex |

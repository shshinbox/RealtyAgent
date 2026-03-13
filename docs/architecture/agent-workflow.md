# 에이전트 워크플로우

## 개요

RealtyAgent의 워크플로우는 **LangGraph** 기반의 유향 그래프(DAG)로 구성됩니다.
Planner가 사용자 의도를 분석하여 실행 노드 순서(`node_stack`)를 계획하고,
Dispatcher가 이를 순차적으로 실행하는 구조입니다.

---

## 전체 흐름도

```
사용자 질문 입력
      │
      ▼
 Initializer          세션 초기화, 대화 이력 로딩
      │
      ▼
   Planner            의도 분석 → node_stack 생성
      │
      ▼
  Dispatcher ◄────────────────────────────────────┐
      │                                           │
      │ node_stack에서 다음 노드 pop                │
      │                                           │
      ├──► LegalRetriever                         │
      │         │  법령/판례 검색                   │
      │         ▼                                 │
      ├──► DocRetriever      ──► Verifier ────────┤ (재검색 또는 Dispatcher 복귀)
      │         │  공문서 검색       │              │
      │         ▼                  │ 검증 실패      │
      ├──► MemoryRetriever         │ → 재호출       │
      │         │  과거 맥락 조회    │               │
      │         └──────────────────┘               │
      │                                            │
      ├──► Generator                               │
      │         │  리포트 JSON 생성                  │
      │         ▼                                  │
      │      Evaluator                             │
      │         │  품질/보안/환각 검사               │
      │         ├── 실패 → Generator 재시도         │
      │         └── 통과 → Dispatcher 복귀 ─────────┘
      │
      ├──► HumanReviewer
      │         │  중간 승인 요청
      │         ├── REPLAN  → Planner
      │         ├── REWRITE → Generator
      │         └── APPROVE → Dispatcher
      │
      └──► Finalizer
                │  node_stack 소진 시 최종 처리
                ▼
              END
```

---

## 노드 상세

### Initializer
- 세션을 초기화하고 PostgreSQL에서 대화 이력을 로딩합니다.
- 이후 모든 노드가 공유할 `AgentState`를 구성합니다.

### Planner
- 사용자 질문을 분석하여 아래 세 가지를 생성합니다.

| 출력 필드 | 설명 |
|---|---|
| `intention` | 사용자 의도 한 문장 요약 |
| `refined_query` | 검색 최적화된 쿼리 |
| `node_stack` | 실행할 노드 순서 리스트 |

- 사용 가능한 노드: `legal_retriever`, `doc_retriever`, `memory_retriever`, `generator`, `human_reviewer`
- `initializer`, `planner`, `dispatcher`, `verifier`, `evaluator`, `finalizer`는 시스템이 자동 관리하며 Planner가 직접 지정하지 않습니다.

### Dispatcher
- `node_stack`에서 노드를 순차적으로 pop하여 다음 실행 노드를 결정합니다.
- `node_stack`이 소진되면 `Finalizer`로 라우팅합니다.

### LegalRetriever
- 법령 해석례, 판례 등 법적 근거를 외부 API 및 Vector DB에서 검색합니다.
- 검색 완료 후 `Verifier`로 전달됩니다.

### DocRetriever
- 매물 정보, 실거래가, 공문서 등 사실 관계 데이터를 Vector DB에서 검색합니다.
- 검색 완료 후 `Verifier`로 전달됩니다.

### MemoryRetriever
- PostgreSQL에서 사용자의 과거 대화 이력 및 GLiNER 추출 프로필을 조회합니다.
- 검색 완료 후 `Verifier`로 전달됩니다.

### Verifier
- 검색 결과의 유효성을 검증합니다.
- 검증 실패 시 동일 노드를 재호출합니다.
- **Circuit Breaker**: 동일 노드 재호출 횟수가 3회를 초과하면 강제로 `Dispatcher`로 복귀합니다.

```
검증 실패 → 동일 노드 재호출 (최대 3회)
검증 통과 또는 한도 초과 → Dispatcher 복귀
```

### Generator
- 검색된 정보(`retrieved_docs`)를 기반으로 구조화된 리포트 JSON을 생성합니다.
- 근거가 부족한 항목은 "추가 확인 필요"로 명시합니다.
- 생성 완료 후 `Evaluator`로 전달됩니다.

### Evaluator
- 생성된 결과물에 대해 아래 세 가지를 검사합니다.

| 검사 항목 | 설명 |
|---|---|
| `is_secured` | 프롬프트 인젝션 공격 여부 |
| `is_grounded` | 환각(Hallucination) 여부 |
| `has_pii` | 개인정보 포함 여부 |

- 검사 통과 시 `Dispatcher`로 복귀합니다.
- 검사 실패 시 `Generator` 재시도 또는 `HumanReviewer`로 라우팅합니다.

### HumanReviewer
- 중간 결과물에 대한 사용자 승인을 요청합니다.
- 사용자 피드백에 따라 세 가지 경로로 분기합니다.

| 액션 | 다음 노드 | 설명 |
|---|---|---|
| `REPLAN` | Planner | 전략 자체를 재수립 |
| `REWRITE` | Generator | 현재 검색 결과 기반으로 재작성 |
| `APPROVE` | Dispatcher | 승인 후 다음 단계 진행 |

### Finalizer
- `node_stack`이 소진된 최종 단계에서 호출됩니다.
- 결과를 정리하고 Redis를 통해 Worker(GLiNER 엔티티 추출 등) 태스크를 발행합니다.

---

## 상태 관리 (AgentState)

모든 노드는 `AgentState`를 공유하며, 각 노드는 필요한 필드만 읽고 씁니다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `messages` | `List[BaseMessage]` | 전체 대화 메시지 이력 |
| `query` | `str` | 원본 사용자 질문 |
| `planner_response` | `PlannerResponse` | Planner 출력 (node_stack, refined_query, intention) |
| `next_node` | `NodeType` | Dispatcher가 라우팅할 다음 노드 |
| `retrieved_docs` | `dict` | 각 Retriever가 수집한 검색 결과 |
| `human_feedback` | `HumanFeedback` | HumanReviewer로부터의 사용자 피드백 |
| `evaluation_response` | `EvaluationResponse` | Evaluator 검사 결과 |
| `circuit_check` | `CircuitCheck` | 노드별 재호출 횟수 추적 |
| `answer` | `str` | Generator 최종 생성 결과 |
| `retry_count` | `int` | 재시도 횟수 |

---

## 라우팅 요약

| 출발 노드 | 조건 | 다음 노드 |
|---|---|---|
| Dispatcher | node_stack 다음 항목 | 해당 노드 |
| Dispatcher | node_stack 소진 | Finalizer |
| Verifier | 검증 실패 + 한도 미만 | 동일 Retriever 재호출 |
| Verifier | 검증 통과 또는 한도 초과 | Dispatcher |
| Evaluator | 통과 | Dispatcher |
| Evaluator | 실패 | Generator 또는 HumanReviewer |
| HumanReviewer | REPLAN | Planner |
| HumanReviewer | REWRITE | Generator |
| HumanReviewer | APPROVE | Dispatcher |

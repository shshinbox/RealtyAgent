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
  Dispatcher ◄─────────────────────────────────────┐
      │                                            │
      │ node_stack에서 다음 노드 pop                 │
      │                                            │
      ├──► Counselor ◄───────────────────┐         │
      │         │  정보 수집 상담          │         │
      │         │  (interrupt_after)     │         │
      │         ├── is_ready=False ──────┘         │
      │         └── is_ready=True ──► Dispatcher ──┤
      │                                            │
      ├──► LegalRetriever ◄───────────┐            │
      │         │  법령/판례 검색       │            │
      │         ├── 검증 실패 ─────────┘             │
      │         └── 검증 통과/한도 초과 ─► Dispatcher─┤
      │                                             │
      ├──► DocRetriever ◄────────────┐              │
      │         │  공문서 검색        │              │
      │         ├── 검증 실패 ────────┘              │
      │         └── 검증 통과/한도 초과 ─► Dispatcher─┤
      │                                             │
      ├──► MemoryRetriever ─────────────────────────┤
      │         │  과거 맥락 조회 (항상 Dispatcher 복귀) │
      │                                            │
      ├──► Generator                               │
      │         │  문서 유형별 결과 생성              │
      │         ▼                                  │
      │      Evaluator                             │
      │         │  품질/보안/환각 검사               │
      │         ├── 실패 → Generator 재시도         │
      │         └── 통과 → Dispatcher 복귀 ─────────┘
      │
      ├──► HumanReviewer
      │         │  중간 승인 요청 (interrupt_before)
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

- 사용 가능한 노드: `counselor`, `legal_retriever`, `doc_retriever`, `memory_retriever`, `generator`, `human_reviewer`
- `initializer`, `planner`, `dispatcher`, `evaluator`, `finalizer`는 시스템이 자동 관리하며 Planner가 직접 지정하지 않습니다.
- 문서 작성이 필요한 요청에는 `counselor`를 `generator` 앞에 배치하여 필요 정보를 사전 수집합니다.

### Dispatcher
- `node_stack`에서 노드를 순차적으로 pop하여 다음 실행 노드를 결정합니다.
- `node_stack`이 소진되면 `Finalizer`로 라우팅합니다.

### LegalRetriever
- 법령 해석례, 판례 등 법적 근거를 외부 API 및 Vector DB에서 검색합니다.
- 검색 완료 후 내부에서 결과 유효성을 검증합니다(doc 길이 + 프롬프트 인젝션 검사).
- **Circuit Breaker**: 검증 실패 시 자기 자신으로 재시도하며 3회 초과 시 `Dispatcher`로 복귀합니다.

### DocRetriever
- 매물 정보, 실거래가, 공문서 등 사실 관계 데이터를 Vector DB에서 검색합니다.
- LegalRetriever와 동일한 self-loop 검증 구조를 가집니다.

### MemoryRetriever
- PostgreSQL에서 사용자의 과거 대화 이력 및 GLiNER 추출 프로필을 조회합니다.
- 실패 시 빈 값으로 처리하며 항상 `Dispatcher`로 복귀합니다 (재시도 없음).

### Counselor
- 문서 작성 전 사용자와 대화하며 필요한 정보를 한 항목씩 수집합니다.
- `interrupt_after`로 동작하며, 실행 직후 그래프가 일시 중단되어 사용자 응답을 기다립니다.
- `resume(feedback)`으로 사용자 답변이 주입되면 다음 턴이 실행됩니다.
- 질문은 `counselor_question` state 필드를 통해 프론트엔드에 전달됩니다 (`answer`와 분리).
- 필수 정보가 모두 수집되면(`is_ready=True`) `Dispatcher`로 복귀하여 다음 노드로 진행합니다.
- 수집된 정보는 `ConsultationContext`에 누적되며, `Generator`가 문서 생성 시 이를 참조합니다.

**지원 문서 유형 및 필수 수집 항목:**

| 문서 유형 | 필수 항목 |
|---|---|
| `legal_report` | 상담 주제, 분쟁 상황, 관련 당사자 |
| `lease_contract` | 임대인/임차인 정보, 부동산 소재지, 보증금, 임대료, 임대 기간 |
| `sale_contract` | 매도인/매수인 정보, 부동산 소재지, 매매 대금, 계약금·중도금·잔금 일정 |
| `legal_memo` | 발신인/수신인 정보, 작성 목적, 관련 사실 관계 |

### Generator
- `ConsultationContext`의 `document_type`을 런타임에 읽어 해당 YAML 프롬프트 템플릿을 동적으로 로딩합니다.
- 검색된 정보(`retrieved_docs`)와 상담 컨텍스트(`consultation_context`)를 결합하여 결과물을 생성합니다.
- 근거가 부족한 항목은 "추가 확인 필요"로 명시합니다.
- 생성 완료 후 `Evaluator`로 전달됩니다.

**문서 유형별 YAML 템플릿 (`engine/statics/generator/`):**

| 파일 | 문서 유형 | 설명 |
|---|---|---|
| `chat.yaml` | `chat` | 가벼운 대화형 응답 (기본값) |
| `legal_report.yaml` | `legal_report` | 법률 상담 리포트 |
| `lease_contract.yaml` | `lease_contract` | 임대차 계약서 |
| `sale_contract.yaml` | `sale_contract` | 매매 계약서 |
| `legal_memo.yaml` | `legal_memo` | 내용증명 / 법률 메모 |

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
- `interrupt_before`로 동작하며, 노드 실행 전 그래프가 일시 중단되어 사용자 피드백을 기다립니다.
- `resume(feedback)`으로 주입된 텍스트를 LLM이 분석하여 `HumanAction`으로 분류합니다.
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
| `human_feedback` | `HumanFeedback` | HumanReviewer 내부에서 생성된 피드백 분류 결과 |
| `evaluation_response` | `EvaluationResponse` | Evaluator 검사 결과 |
| `circuit_check` | `CircuitCheck` | 노드별 재호출 횟수 추적 |
| `answer` | `str` | Generator 최종 생성 결과 (Counselor 질문과 분리) |
| `retry_count` | `int` | 재시도 횟수 |
| `consultation_context` | `ConsultationContext` | Counselor가 턴마다 누적하는 상담 정보 (문서 유형 + 동적 필드) |
| `user_input` | `str` | 단일 입력 채널. `resume()`으로 주입되며 Counselor·HumanReviewer가 공유 |
| `counselor_question` | `str` | Counselor가 프론트엔드에 전달하는 현재 질문 (`answer`와 별도 채널) |

---

## 라우팅 요약

| 출발 노드 | 조건 | 다음 노드 |
|---|---|---|
| Dispatcher | node_stack 다음 항목 | 해당 노드 |
| Dispatcher | node_stack 소진 | Finalizer |
| Counselor | `is_ready=False` | Counselor (자기 자신, 루프) |
| Counselor | `is_ready=True` | Dispatcher |
| LegalRetriever | 검증 실패 + 한도 미만 | LegalRetriever (자기 자신, 루프) |
| LegalRetriever | 검증 통과 또는 한도 초과 | Dispatcher |
| DocRetriever | 검증 실패 + 한도 미만 | DocRetriever (자기 자신, 루프) |
| DocRetriever | 검증 통과 또는 한도 초과 | Dispatcher |
| MemoryRetriever | 항상 | Dispatcher |
| Evaluator | 통과 | Dispatcher |
| Evaluator | 실패 | Generator 또는 HumanReviewer |
| HumanReviewer | REPLAN | Planner |
| HumanReviewer | REWRITE | Generator |
| HumanReviewer | APPROVE | Dispatcher |

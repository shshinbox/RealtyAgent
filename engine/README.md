# Agentic Workflow Engine

본 프로젝트는 **LangGraph**를 활용하여 개발한 **상태(State) 기반 AI 작업 관리 엔진**입니다. 사용자 요구사항에 따라 적절한 도구를 선택하고, 실행 결과를 검증하여 답변을 생성하는 순환형 구조로 설계하였습니다.

---

## 🔄 Workflow

공유 상태(State)를 기반으로 각 노드가 정의된 규칙에 따라 동작하도록 구성함

1. **초기화 (Initialization)**: 사용자 입력 쿼리의 프롬프트 주입(Prompt Injection) 공격 여부 검증
2. **계획 수립 (Planning)**: 질문 분석 후 정제된 쿼리 생성 및 실행 단계(Task Stack) 수립
3. **작업 할당 (Dispatching)**: 계획에 맞춰 법령 검색(Legal), 문서 추출(Doc) 등 워커 노드에 작업 배분
4. **인자 생성 (Parameter Fitting)**: 호출할 API 규격에 맞춰 LLM이 실시간으로 파라미터 조립 및 실행
5. **실행 결과 검증 (Verifier)**: 외부에서 유입된 문서 내에 포함된 프롬프트 공격 요소를 탐지하고 데이터의 유효성 체크
6. **답변 생성 (Generation)**: 검증된 데이터를 바탕으로 최종 답변 조립
7. **품질 및 안전 검토 (Evaluation)**: 최종 답변의 **할루시네이션(Hallucination)**, **개인정보(PII)** 포함 여부, **프롬프트 공격** 여부 검증
8. **사용자 개입 (Human-in-the-loop)**: 검증 결과가 기준 미달이거나 판단이 모호한 경우 사용자 피드백을 수집하여 계획 수정 또는 작업 재개
---

## 🛠 주요 고려 사항

### 1. 비용 절감 및 LLM 의존도 조정
* **중앙 제어 최소화**: 모든 판단을 LLM 수퍼바이저 노드에게 맡기는 대신, 정해진 상태값에 따라 다음 노드를 결정하는 방식을 채택
* **토큰 소모 최적화**: 불필요한 추론 과정을 줄여 운영 비용을 낮추고 실행 속도를 높임

### 2. API 규격 대응 (Strict API Interaction)
* **규격 일치**: 벡터 DB 검색(RAG)과 달리 일반 API는 파라미터 값이 엄격해야 함. 이를 해결하기 위해 LLM의 역할을 API 인자 생성에 집중시킴
* **전용 프롬프트 활용**: 일반 대화와 분리된 '인자 생성 전용 프롬프트'를 사용하여 호출 정확도를 높임
* **피드백 기반 재시도**: API 응답이 부실할 경우 사용자의 피드백을 반영하여 인자를 다시 구성하고 재호출하는 구조를 만듦

### 3. 타입 정의 및 검증
* **클래스 설계**: `LLMNode[T]`, `ToolNode[P]`와 같은 제네릭 클래스를 정의하여 구조화함
* **데이터 검증**: Pydantic을 활용해 LLM 응답이 정해진 형식을 지키는지 확인하고, 틀릴 경우 런타임 에러 처리를 수행함

---

## 🧬 클래스 계층

```text
BaseNode (Abstract Interface)
│
├── LLMNode[T] (Reasoning & Security)
│   ├── Initializer   : 입력 쿼리 보안 검증 (Prompt Injection)
│   ├── Planner       : 실행 전략 및 Task Stack 수립
│   ├── Verifier      : 외부 문서 보안 검증 및 실행 결과 유효성 체크
│   ├── Generator     : 최종 답변 조립 및 문장 생성
│   ├── Evaluator     : 최종 응답 품질(Hallucination) 및 안전성(PII, Injection) 측정
│   └── HumanReviewer : 사용자 피드백 해석 및 작업 방향 결정
│
├── ToolNode[P] (Integration & Tools)
│   ├── LegalRetriever : 국가 법령 정보 API 연동
│   └── DocRetriever   : 내부 가이드라인 및 매물 문서 검색
│
└── Dispatcher (Orchestration)
    └── Task Stack 제어 및 워커 노드 동적 할당
```

## 🧬 구조도 도식화
```text
[ User Query ]
      |
      v
+------------------+
|   Initializer    | (Input Security Check)
+------------------+
      |
      v
+------------------+
|     Planner      | <--------------------------+
+------------------+                            |
      |                                         |
      v                                         |
+------------------+                            |
|    Dispatcher    | <------------------+       |
+------------------+                    |       |
      |            |                    |       |
      |      [Task 남음]                 |       |
      |            v                    |       |
      |    +----------------+           |       |
      |    |  Worker Node   | (API Call)|       |
      |    +----------------+           |       |
      |            |                    |       |
      |            v                    |       |
      |    +----------------+           |       |
      |    |    Verifier    | ----------+       | (REPLAN)
      |    +----------------+ (Doc Security Check)
      |                                         |
 [Task 완료]                                     |
      |                                         |
      v                                         |
+------------------+                            |
|    Generator     | (Final Synthesis) <--------+ (REWRITE)
+------------------+                            |
      |                                         |
      v                                         |
+------------------+                            |
|    Evaluator     | (PII/Hallucination Check)  |
+------------------+                            |
      |                                         |
      | [검증 실패 시]                            |
      v                                         |
+------------------+                            |
|  Human Reviewer  | (User Feedback)            |
+------------------+ ---------------------------+
      |
 [최종 통과]
      |
      v
 [ Final Answer ]
 ```
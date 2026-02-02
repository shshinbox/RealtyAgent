# RealtyAgent

## 📌 개요

본 프로젝트는 기존 버전([real-estate-agent](https://github.com/shshinbox/real-estate-agent))에서의 선형적 워크플로우의 한계와 상태 제어의 어려움을 극복하기 위해 LangGraph를 도입한 고도화 버전입니다.

단순 답변 생성을 넘어 도구 선택과 결과 검증, 그리고 API 조회 결과가 불충분할 경우 검색 쿼리를 재구성하여 재시도하는 자가 수정 기능을 수행하는 상태(State) 기반 순환형 엔진을 지향합니다.

---


## 🛠️ 적용 기술

| Category          | Technology            |
| :---------------- | :-------------------- |
| **Framework**     | LangGraph, LangChain  |
| **LLM**           | GPT-4o                |
| **Database**      | PostgreSQL            |
| **Persistence**   | AsyncSqliteSaver      |
| **Vector DB**     | Qdrant                |
| **Data Modeling** | Pydantic v2           |
| **Environment**   | Python 3.12+, Asyncio |

---

## 🧬 구조도 도식화
```text
         [ User Query ]
               |
               v
         +-------------+
         | Initializer | 
         +-------------+
               |
               v
          +-----------+
+-------> |  Planner  |
|         +-----------+                                    
|              |                                          
|              v                        
|         +------------+ --------------------------------> +-----------+
|    +--> | Dispatcher | -----------------------+          | Finalizer | 
|    |    +------------+ <---------+            |          +-----------+ 
|    |         |                   |            |                |
|    |   (Select Worker)           |            |                v
|    |         v                   |            |             [ END ]  
|    |    +-------------+          |            |        
|    |    | Worker Node |          |            |
|    |    | Gen|Tool|Hu |          |            |
|    |    +-------------+          |            |        
|    |         |                   |            |        
|    |         v                   |            |        
|    |    +------------+           |            |        
|    |    |  Verifier  |-----------+            |        
|    |    +------------+ (Success / Max Fail)   |        
|    |                                          |        
|    |        +---------------------------------+        
|    |        | (Empty Task & Answer)                                         
|    |        v                                          
|    |   +-----------+                                   
|    |   | Generator | <------------------------+ (Rewrite)    
|    |   +-----------+                          |        
|    |        |                                 |        
|    |        v                                 |        
|    |   +-----------+      (Review Need)       |       
|    +-- | Evaluator | --------------------+    |        
|    |   +-----------+                     |    |        
|    |                                     |    |        
|    |       (Approve)                     v    |        
|    +----------------------------- +------------------+    
+---------------------------------- |  Human Reviewer  |
             (Replan)               +------------------+
 ```

---


## 🧬 클래스 계층

```text
BaseNode
│
├── LLMNode[T]
│   ├── Initializer   : 상태 초기화 및 입력 쿼리 검증
│   ├── Planner       : 실행 전략 및 Task Stack 수립
│   ├── Verifier      : 외부 문서의 Prompt Injection 체크 및 실행 결과 유효성 체크
│   ├── Generator     : 답변 문장 생성
│   ├── Evaluator     : 최종 응답 Hallucination, 프라이버시(PII), Prompt Injection 체크
│   ├── HumanReviewer : 사용자 피드백 해석 및 작업 방향 결정
│   └── Finalizer     : 상태 정리
│
├── ToolNode[P]
│   ├── LegalRetriever : 국가 법령 정보 API 연동
│   └── DocRetriever   : 내부 문서 검색(Vector DB)
│
└── Dispatcher
    └── Task Stack 제어 및 워커 노드 동적 할당
```

---

## 🔄 워크플로우

공유 상태(State)를 기반으로 각 노드가 정의된 규칙에 따라 동작하도록 구성함

1. **초기화**: 입력 쿼리의 **Prompt Injection** 공격 여부 검증
2. **계획 수립**: 질문 분석 및 실행 단계(`node_stack`) 수립
3. **작업 할당**: 계획에 맞춰 노드(Tool nodes, Generator, HITL)에 작업 배분
4. **실행 결과 검증**: 외부 유입 문서의 공격 요소 탐지 및 데이터 유효성 체크
5. **자가 수정**: API 조회 결과 부재 시, **쿼리를 재구성**하여 재시도 수행
6. **답변 생성**: 검증된 데이터를 바탕으로 최종 답변 생성
7. **품질 및 안전 검토**: 최종 답변의 **Hallucination**, **개인정보(PII)** 포함 여부, **프롬프트 공격** 여부 체크
8. **사용자 개입(HITL)**: 검증 결과가 기준 미달이거나 판단이 모호한 경우 사용자 피드백을 수집하여 계획 수정 또는 작업 재개
9. **상태 정리**: `Finalizer` 노드를 통해 이전 단계의 데이터와 제어 상태 초기화
---

## 🛠 주요 고려사항

복잡한 부동산 및 법률 도메인 상담 시나리오를 해결하기 위해 **자율적 기획(Planning)**, **상태 무결성(State Integrity)**, 그리고 <b>보안 가드레일(Security Guardrail)</b>을 핵심 가치로 설계하였습니다.

---

#### 1. Logic-Centric Orchestration (판단 의존도 최적화)
* **판단 의존도 제어**: 모든 분기점과 판단을 LLM에 과도하게 위임하는 구조를 지양하고, 핵심 비즈니스 로직은 확정적으로 설계하되 유연한 대응이 필수적인 Planner 영역에만 자율성을 선별적으로 부여

#### 2. Dynamic Planning
* **Planner-Executor**: 질문 의도를 분석해 실행 노드(node_stack)를 실시간으로 유연하게 구성
* **선택적 인터럽트**: 사용자 요청 시에만 전략적으로 확인 단계 배치

#### 3. AI Security & Safety
* **노드별 가드레일**: query 및 Retriever 응답 결과 내 인젝션 의심 경고, Generator 출력 후 환각 및 프라이버시 체크

#### 4. Human-in-the-Loop
* **재기획 및 검증**: 사용자 개입 상황을 모사하여 비동기 입력 기반의 피드백을 반영해 이후 실행 계획을 실시간으로 수정

#### 5. Self-Correction
* **자가 수정**: API 결과가 없을 때 쿼리를 재구성하여 재시도를 수행하며, Max Retries 도달 시 다음 단계로 전이

---

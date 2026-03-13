# API 레퍼런스 - Inference

## 개요

RealtyAgent의 핵심 추론 API입니다.
사용자의 질문을 LangGraph 엔진에 전달하고, 처리 결과를 **Server-Sent Events(SSE)** 스트림으로 반환합니다.

모든 엔드포인트는 JWT 인증이 필요합니다.

---

## 인증

모든 요청에 `Authorization` 헤더가 필요합니다.

```
Authorization: Bearer <JWT_TOKEN>
```

JWT 페이로드에 `user_id` 클레임이 포함되어야 합니다.

---

## 엔드포인트

### 1. 새 대화 시작

```
POST /new
```

새로운 `thread_id`를 자동 생성하여 대화를 시작합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `user_query` | string | ✅ | 사용자 질문 |

**Response**

- Content-Type: `text/event-stream`
- 처리 진행 상황 및 최종 결과를 SSE 스트림으로 반환

**Example**

```bash
curl -X POST "http://localhost:8000/new?user_query=전세사기 예방 방법을 알려주세요" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 2. 기존 대화 이어서 질문

```
POST /{thread_id}
```

기존 `thread_id`의 대화 맥락을 유지하며 추가 질문을 전달합니다.

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `user_query` | string | ✅ | 사용자 질문 |

**Response**

- Content-Type: `text/event-stream`

**Example**

```bash
curl -X POST "http://localhost:8000/{thread_id}?user_query=계약서에서 확인해야 할 항목은?" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 3. HumanReview 후 재개

```
POST /{thread_id}/resume
```

`HumanReviewer` 노드에서 대기 중인 워크플로우에 사용자 피드백을 전달하고 실행을 재개합니다.

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `feedback` | string | ✅ | 사용자 피드백 내용 |

**피드백 처리 결과**

엔진 내부에서 피드백을 분석하여 아래 세 가지 액션 중 하나로 분기합니다.

| 액션 | 설명 |
|---|---|
| `REPLAN` | Planner로 돌아가 실행 계획 재수립 |
| `REWRITE` | Generator로 돌아가 답변 재생성 |
| `APPROVE` | 승인 처리 후 다음 단계 진행 |

**Response**

- Content-Type: `text/event-stream`

**Example**

```bash
curl -X POST "http://localhost:8000/{thread_id}/resume?feedback=법적 근거를 더 자세히 설명해주세요" \
  -H "Authorization: Bearer <TOKEN>"
```

---

### 4. 대화 상태 조회

```
GET /{thread_id}/state
```

특정 스레드의 현재 에이전트 상태를 조회합니다.

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Response**

```json
{
  "query": "사용자 원본 질문",
  "answer": "최종 생성된 답변",
  "planner_response": {
    "intention": "사용자 의도 요약",
    "refined_query": "최적화된 검색 쿼리",
    "node_stack": []
  },
  "retrieved_docs": { ... },
  "retry_count": 0
}
```

**Error**

| 코드 | 설명 |
|---|---|
| `404` | 해당 thread_id의 상태 없음 |

---

### 5. 리포트 다운로드

```
GET /{thread_id}/download
```

최종 생성된 답변을 HTML 파일로 렌더링하여 다운로드합니다.

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Response**

- Content-Type: `text/html`
- 파일명: `{thread_id}.html`

**Error**

| 코드 | 설명 |
|---|---|
| `404` | 생성된 답변 없음 |

---

## SSE 응답 형식

스트리밍 응답은 `text/event-stream` 형식으로 전달되며, 각 이벤트는 아래 형식을 따릅니다.

```
data: <HTML 렌더링된 청크>\n\n
```

노드 실행 진행 상황과 최종 결과가 순차적으로 스트리밍됩니다.

---

## 공통 에러 코드

| 코드 | 설명 |
|---|---|
| `401` | 인증 실패 또는 토큰 만료 |
| `500` | SECRET_KEY 미설정 등 서버 설정 오류 |

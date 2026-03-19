# API 레퍼런스

## 개요

RealtyAgent의 핵심 API입니다.
추론 엔드포인트는 처리 결과를 **Server-Sent Events(SSE)** 스트림으로 반환합니다.

인증 엔드포인트(`POST /token`)를 제외한 모든 엔드포인트는 JWT 인증이 필요합니다.

---

## 인증

### 로그인 토큰 발급

```
POST /token
```

`application/x-www-form-urlencoded` 형식으로 자격증명을 전달합니다.

**Form Parameters**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `username` | string | 설정된 AUTH_USERNAME |
| `password` | string | 설정된 AUTH_PASSWORD |

**Response**

```json
{
  "access_token": "<JWT>",
  "token_type": "bearer"
}
```

발급된 토큰은 이후 요청의 `Authorization` 헤더에 포함합니다.

```
Authorization: Bearer <JWT_TOKEN>
```

JWT 페이로드에 `user_id` 클레임이 포함됩니다. 유효 시간은 발급 후 24시간입니다.

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
curl -X POST "http://localhost:8000/new?user_query=여기에 질문을 입력하세요" \
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

### 4. 대화 히스토리 조회

```
GET /chat/{thread_id}/history
```

페이지 접근 시 이전 대화 내역과 보고서를 복원하기 위해 사용합니다.
프론트엔드는 `/c/{thread_id}` URL 진입 시 자동으로 이 API를 호출합니다.

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Response**

```json
{
  "messages": [
    { "type": "human", "content": "사용자 메시지" },
    { "type": "ai",    "content": "AI 응답 메시지" }
  ],
  "report_html": "<div class=\"lr-report\">...</div>"
}
```

- `report_html`: 마지막으로 생성된 보고서의 렌더링된 HTML. 없으면 `null`.

**Error**

| 코드 | 설명 |
|---|---|
| `404` | 해당 thread_id 없음 |

---

### 5. 대화 상태 조회

```
GET /chat/{thread_id}/state
```

특정 스레드의 현재 에이전트 상태를 조회합니다. (내부 디버깅용)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `thread_id` | string (UUID) | ✅ | 대화 스레드 ID |

**Response**

```json
{
  "query": "사용자 원본 질문",
  "answer": "최종 생성된 답변 (JSON 문자열 또는 plain text)",
  "chat_message": "Generator가 생성한 짧은 채팅 안내",
  "planner_response": {
    "intention": "사용자 의도 요약",
    "refined_query": "최적화된 검색 쿼리",
    "planned_nodes": [],
    "document_type": "chat"
  },
  "retrieved_docs": {},
  "retry_count": 0
}
```

**Error**

| 코드 | 설명 |
|---|---|
| `404` | 해당 thread_id의 상태 없음 |

---

### 6. 리포트 다운로드

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

스트리밍 응답은 `text/event-stream` 형식으로 전달됩니다.

```
data: <HTML 청크>\n\n
```

### 청크 종류

프론트엔드는 CSS 클래스 및 속성으로 청크 종류를 구분합니다.

| 청크 형태 | CSS 클래스 / 속성 | 렌더링 위치 | 설명 |
|---|---|---|---|
| `<div class="ai-chunk">` | `ai-chunk` | 왼쪽 상태 뱃지 | 노드 진행 상태 메시지 |
| `<div class="ai-chunk" data-event="pause">` | `ai-chunk` + `data-event=pause` | 리뷰 툴바 표시 | HumanReviewer 대기 시작 |
| `<div class="ai-counselor-chunk">` | `ai-counselor-chunk` | 왼쪽 AI 말풍선 | Counselor 질문 또는 chat 모드 최종 답변 |
| `<div class="ai-report-chunk">` | `ai-report-chunk` | 오른쪽 보고서 패널 | 보고서 모드 최종 답변 (렌더링된 HTML) |

### 특수 이벤트

`POST /chat/new` 응답의 첫 번째 청크는 thread_id 이벤트입니다.

```
data: thread_id:<UUID>\n\n
```

프론트엔드는 이 값을 받아 브라우저 URL을 `/c/{thread_id}`로 변경합니다 (`history.pushState`).

---

## 공통 에러 코드

| 코드 | 설명 |
|---|---|
| `401` | 인증 실패 또는 토큰 만료 |
| `500` | SECRET_KEY 미설정 등 서버 설정 오류 |

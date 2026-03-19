# 프론트엔드 구조

## 개요

RealtyAgent 프론트엔드는 프레임워크 없이 Vanilla HTML/CSS/JS로 구성된 **SPA(Single Page Application)**입니다.

---

## 파일 구성

```
frontend/
  index.html          단일 HTML 페이지 (분할 패널 레이아웃)
  static/
    style.css         전체 스타일
    chat.js           SSE 스트리밍, 히스토리 로딩, 이벤트 처리
```

---

## 화면 레이아웃

```
┌──────────────────────────┬──────────────────────────────┐
│      왼쪽: 채팅 패널       │      오른쪽: 보고서 패널        │
│  ┌────────────────────┐   │                             │
│  │  사용자 메시지       │   │   법률 리포트 / 계약서 등      │
│  │  AI 말풍선          │   │   (Jinja2 렌더링 HTML)       │
│  │  진행 상태 뱃지      │   │                             │
│  └────────────────────┘   │                             │
│  [입력창]  [전송]          │                   [다운로드]  │
└──────────────────────────┴──────────────────────────────┘
```

- 좌측 채팅 패널 너비: 420px (CSS 변수 `--chat-width`)
- 우측 보고서 패널: `1fr` (나머지 전체)

---

## 상태 관리

`chat.js` 최상단에서 세 가지 상태를 관리합니다.

| 변수 | 타입 | 설명 |
|---|---|---|
| `threadId` | `string \| null` | 현재 대화 스레드 ID. 없으면 `/chat/new`로 시작 |
| `isPaused` | `boolean` | HumanReviewer 대기 중 여부. `true`이면 입력창 숨김, 리뷰 툴바 표시 |
| `isStreaming` | `boolean` | SSE 스트리밍 중 여부. `true`이면 입력 비활성화 |

---

## 인증

- JWT 토큰을 `localStorage["jwt_token"]`에 저장합니다.
- 토큰이 없으면 페이지 상단에 토큰 입력 배너가 표시됩니다.
- 토큰 발급은 `POST /token` 엔드포인트를 사용합니다. ([API 레퍼런스](./api-reference.md) 참고)
- 모든 API 요청에 `Authorization: Bearer <token>` 헤더를 포함합니다.

---

## SSE 스트리밍

`EventSource` 대신 `fetch` + `ReadableStream`을 사용합니다.
`EventSource`는 POST 요청과 커스텀 헤더(JWT)를 지원하지 않기 때문입니다.

```
streamRequest(url, body?)
  └─ fetch(POST) → ReadableStream reader
       └─ buffer.split("\n\n") → handleSseChunk(rawHtml)
```

### SSE 청크 라우팅

`handleSseChunk()`가 수신된 HTML의 CSS 클래스를 파싱하여 렌더링 위치를 결정합니다.

| 조건 | 처리 |
|---|---|
| `rawHtml.startsWith("thread_id:")` | threadId 저장 + URL을 `/c/{id}`로 변경 (`history.pushState`) |
| `cls.includes("ai-report-chunk")` | `renderReport(el.innerHTML)` → 오른쪽 패널 |
| `cls.includes("ai-counselor-chunk")` | `appendAiMessage(text)` → 왼쪽 AI 말풍선 |
| `el.dataset.event === "pause"` | `showReviewToolbar()` → HumanReviewer 피드백 UI 표시 |
| `cls.includes("ai-chunk")` | 상태 뱃지 텍스트 업데이트 |

---

## URL 관리 (SPA 라우팅)

| URL 패턴 | 동작 |
|---|---|
| `/` | 새 대화 시작 화면 |
| `/c/{thread_id}` | 기존 대화 복원. 페이지 로드 시 `GET /chat/{thread_id}/history` 자동 호출 |

새 대화가 시작되면 서버가 SSE 첫 이벤트로 `thread_id:{uuid}`를 전송하고,
`chat.js`가 `history.pushState()`로 URL을 `/c/{thread_id}`로 변경합니다.

---

## 히스토리 복원

`/c/{thread_id}` URL로 진입하면 `loadHistory(tid)`가 실행됩니다.

```
GET /chat/{thread_id}/history
  └─ messages: 순서대로 사용자/AI 말풍선 렌더링
  └─ report_html: 오른쪽 패널에 innerHTML으로 주입
```

---

## HumanReviewer 흐름

```
SSE: data-event="pause"
  → showReviewToolbar()     입력창 숨김, 리뷰 툴바 표시

사용자가 [재계획 / 재작성 / 승인] 클릭
  → handleReview(action)
  → POST /chat/{thread_id}/resume  { feedback: "action:comment" }
  → hideReviewToolbar()            리뷰 툴바 숨김, 입력창 복원
```

---

## 보고서 렌더링

`renderReport(html)`은 서버에서 이미 렌더링된 HTML을 그대로 `innerHTML`로 주입합니다.
서버(`html_renderer.py`)가 `answer` JSON을 파싱하여 `legal_report_panel.html` Jinja2 템플릿으로 렌더링합니다.

| document_type | 렌더링 방식 |
|---|---|
| `chat` | 오른쪽 패널 미사용. `answer` 텍스트를 왼쪽 AI 말풍선에 표시 |
| `legal_report` | `legal_report_panel.html` 템플릿으로 구조화된 HTML 렌더링 |
| 나머지 보고서 | 현재 plain text fallback (`lr-plain`). 추후 전용 템플릿 추가 예정 |

---

## CSS 주요 클래스

| 클래스 | 설명 |
|---|---|
| `.msg-user` | 사용자 메시지 말풍선 (우측 정렬, 보라색) |
| `.msg-ai` | AI 메시지 말풍선 (좌측 정렬, 회색 배경) |
| `.msg-status` | 진행 상태 뱃지. `.done` 추가 시 펄스 애니메이션 정지 |
| `.report-content` | 오른쪽 패널 콘텐츠 영역 |
| `.lr-report` | 법률 리포트 최상위 컨테이너 |
| `.lr-section` | 리포트 내 섹션 (핵심 쟁점, 법적 근거 등) |
| `.lr-ground` | 법적 근거 카드 (좌측 보라색 보더) |
| `.lr-list--advice` | 실무 조언 리스트 (초록 마커) |
| `.lr-list--caution` | 주의사항 리스트 (빨간 마커) |

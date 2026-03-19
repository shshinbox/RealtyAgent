(() => {
  // ── 상태 ──────────────────────────────────────────
  let threadId = null;      // 현재 대화 스레드 ID
  let isPaused = false;     // human_reviewer 대기 중 여부
  let isStreaming = false;  // SSE 스트리밍 중 여부

  // JWT 토큰: localStorage["jwt_token"]에서 읽음
  function getToken() {
    return localStorage.getItem("jwt_token") || "";
  }

  // ── DOM ───────────────────────────────────────────
  const chatMessages   = document.getElementById("chat-messages");
  const userInput      = document.getElementById("user-input");
  const btnSend        = document.getElementById("btn-send");
  const btnNewChat     = document.getElementById("btn-new-chat");
  const btnDownload    = document.getElementById("btn-download");
  const reviewToolbar  = document.getElementById("review-toolbar");
  const reviewComment  = document.getElementById("review-comment");
  const chatInputArea  = document.getElementById("chat-input-area");
  const reportContent  = document.getElementById("report-content");

  // ── 토큰 배너 초기화 ──────────────────────────────
  const tokenBanner  = document.getElementById("token-banner");
  const tokenInput   = document.getElementById("token-input");
  const btnSetToken  = document.getElementById("btn-set-token");

  if (!getToken()) tokenBanner.hidden = false;

  // ── URL에서 thread_id 복원 ─────────────────────────
  const urlThreadId = location.pathname.match(/^\/c\/([^/]+)$/)?.[1];
  if (urlThreadId) {
    threadId = urlThreadId;
    loadHistory(urlThreadId);
  }

  btnSetToken.addEventListener("click", () => {
    const val = tokenInput.value.trim();
    if (!val) return;
    localStorage.setItem("jwt_token", val);
    tokenBanner.hidden = true;
  });

  // ── 이벤트 바인딩 ─────────────────────────────────
  btnSend.addEventListener("click", handleSend);
  btnNewChat.addEventListener("click", resetChat);
  btnDownload.addEventListener("click", handleDownload);

  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // textarea 자동 높이
  userInput.addEventListener("input", () => {
    userInput.style.height = "auto";
    userInput.style.height = userInput.scrollHeight + "px";
  });

  // human_reviewer 버튼들
  document.querySelectorAll(".btn-review").forEach((btn) => {
    btn.addEventListener("click", () => handleReview(btn.dataset.action));
  });

  // ── 핵심 함수 ─────────────────────────────────────

  function handleSend() {
    const query = userInput.value.trim();
    if (!query || isStreaming) return;

    appendUserMessage(query);
    userInput.value = "";
    userInput.style.height = "auto";

    if (!threadId) {
      startNewChat(query);
    } else {
      continueChat(query);
    }
  }

  async function handleReview(action) {
    const comment = reviewComment.value.trim();
    // feedback 문자열: "action:comment" 형태로 백엔드에 전달
    const feedback = comment ? `${action}:${comment}` : action;

    hideReviewToolbar();
    reviewComment.value = "";

    appendStatusMessage(`피드백 전송 중... (${actionLabel(action)})`);
    await streamRequest(`/chat/${threadId}/resume`, { feedback });
  }

  function handleDownload() {
    if (!threadId) return;
    window.open(`/chat/${threadId}/download`, "_blank");
  }

  // ── 히스토리 로딩 ────────────────────────────────

  async function loadHistory(tid) {
    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(`/chat/${tid}/history`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) return;

      const data = await res.json();

      for (const msg of data.messages) {
        if (msg.type === "human") appendUserMessage(msg.content);
        else if (msg.type === "ai") appendAiMessage(msg.content);
      }

      if (data.report_html) {
        renderReport(data.report_html);
        btnDownload.hidden = false;
      }
    } catch (e) {
      console.error("history load failed:", e);
    }
  }

  // ── SSE 스트리밍 ──────────────────────────────────

  async function startNewChat(query) {
    await streamRequest(`/chat/new?user_query=${encodeURIComponent(query)}`);
  }

  async function continueChat(query) {
    await streamRequest(`/chat/${threadId}?user_query=${encodeURIComponent(query)}`);
  }

  async function streamRequest(url, body = null) {
    setStreaming(true);

    // 새 thread_id는 /chat/new 응답 전에 uuid를 직접 생성하지 않고
    // 스트리밍 후 /{thread_id}/state 로 확인하는 대신,
    // 백엔드 /chat/new가 threadId를 SSE 첫 이벤트로 보내도록 하거나
    // 여기서는 단순히 fetch + ReadableStream으로 처리한다.

    let statusEl = null;

    try {
      const token = getToken();
      if (!token) {
        appendStatusMessage("로그인이 필요합니다. 토큰을 설정해 주세요.", true);
        setStreaming(false);
        return;
      }

      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: body ? JSON.stringify(body) : undefined,
      });

      if (!res.ok) {
        appendStatusMessage("오류가 발생했습니다.", true);
        setStreaming(false);
        return;
      }

      // 새 대화인 경우 응답 URL에서 thread_id 파싱 시도
      // (백엔드가 Location 헤더를 주지 않으므로 아래 이벤트에서 처리)

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      statusEl = appendStatusMessage("처리 중...");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop(); // 마지막 미완성 부분은 보류

        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          const rawHtml = part.slice(6).trim();
          handleSseChunk(rawHtml, statusEl);
        }
      }

      // 스트림 종료
      if (statusEl && !isPaused) {
        statusEl.classList.add("done");
        statusEl.querySelector
          ? null
          : (statusEl.textContent = statusEl.textContent); // no-op, just in case
      }

      // thread_id 추출: isNew이면 URL 패턴 없이 state API로 가져올 수 없으므로
      // 백엔드가 특별 이벤트를 보낸다 (아래 handleSseChunk에서 처리)

    } catch (err) {
      console.error(err);
      appendStatusMessage("연결 오류가 발생했습니다.", true);
    } finally {
      setStreaming(false);
    }
  }

  /**
   * SSE 청크 1개 처리
   * rawHtml: data: 이후의 원시 HTML 문자열
   *
   * 청크 종류 (css class 기준):
   *   ai-report-chunk    → 오른쪽 보고서 패널
   *   ai-counselor-chunk → 왼쪽 AI 말풍선 (상태 뱃지와 별개)
   *   ai-chunk + data-event="pause" → human_reviewer 피드백 UI
   *   ai-chunk           → 왼쪽 상태 뱃지 업데이트
   */
  function handleSseChunk(rawHtml, statusEl) {
    // thread_id 이벤트 (data: thread_id:<uuid>)
    if (rawHtml.startsWith("thread_id:")) {
      threadId = rawHtml.slice(10).trim();
      history.pushState({ threadId }, "", `/c/${threadId}`);
      return;
    }

    // 임시 DOM 파싱으로 클래스 확인
    const tmp = document.createElement("div");
    tmp.innerHTML = rawHtml;
    const el = tmp.firstElementChild;

    if (!el) return;

    const cls = el.className || "";

    // 1. 보고서 → 오른쪽 패널
    if (cls.includes("ai-report-chunk")) {
      renderReport(el.innerHTML);
      if (statusEl) statusEl.classList.add("done");
      btnDownload.hidden = false;
      return;
    }

    // 2. counselor 질문 → 왼쪽 AI 말풍선 (상태 뱃지 건드리지 않음)
    if (cls.includes("ai-counselor-chunk")) {
      const text = (el.textContent || el.innerText).trim();
      if (statusEl) statusEl.classList.add("done");
      appendAiMessage(text);
      return;
    }

    // 3. pause 마커 → human_reviewer 피드백 UI
    if (el.dataset && el.dataset.event === "pause") {
      isPaused = true;
      showReviewToolbar();
      if (statusEl) statusEl.classList.add("done");
      return;
    }

    // 4. 일반 상태 메시지 → 상태 뱃지 텍스트만 업데이트
    if (cls.includes("ai-chunk")) {
      const text = el.textContent || el.innerText;
      if (statusEl) {
        statusEl.textContent = text;
      } else {
        appendStatusMessage(text);
      }
      return;
    }
  }

  // ── UI 헬퍼 ──────────────────────────────────────

  function appendAiMessage(text) {
    const div = document.createElement("div");
    div.className = "msg-ai";
    div.textContent = text;
    chatMessages.appendChild(div);
    scrollToBottom();
  }

  function appendUserMessage(text) {
    const div = document.createElement("div");
    div.className = "msg-user";
    div.textContent = text;
    chatMessages.appendChild(div);
    scrollToBottom();
  }

  function appendStatusMessage(text, isDone = false) {
    const div = document.createElement("div");
    div.className = "msg-status" + (isDone ? " done" : "");
    div.textContent = text;
    chatMessages.appendChild(div);
    scrollToBottom();
    return div;
  }

  function renderReport(html) {
    reportContent.innerHTML = html;
  }

  function showReviewToolbar() {
    reviewToolbar.hidden = false;
    chatInputArea.hidden = true;
  }

  function hideReviewToolbar() {
    reviewToolbar.hidden = true;
    chatInputArea.hidden = false;
    isPaused = false;
  }

  function setStreaming(val) {
    isStreaming = val;
    btnSend.disabled = val;
    userInput.disabled = val;
  }

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function resetChat() {
    threadId = null;
    isPaused = false;
    chatMessages.innerHTML = "";
    reportContent.innerHTML = `<div class="report-placeholder"><p>대화를 시작하면 보고서가 이곳에 표시됩니다.</p></div>`;
    btnDownload.hidden = true;
    hideReviewToolbar();
  }

  function actionLabel(action) {
    return { replan: "재계획", rewrite: "재작성", approve: "승인" }[action] || action;
  }

})();

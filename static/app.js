"use strict";
(() => {
  const $ = id => document.getElementById(id);
  const roleLabels = {operator: "운영 담당", it: "IT 담당", reviewer: "검토자"};
  const kindLabels = {log: "LOG", runbook: "RUNBOOK", trace: "TRACE"};
  const modeLabels = {baseline: "규칙 기준선 · 추론 없음", ollama: "실제 모델 추출 + 관측 규칙 · Ollama", mock: "모의 모델 · 테스트", degraded: "모델 실패 · 제한된 결과"};
  const statusLabels = {open: "진행 중", investigating: "조사 중", resolved: "해결됨", pending_review: "검토 대기", draft: "초안", ready: "검토 대기", completed: "분석 완료", degraded: "모델 실패", failed: "실패", approved: "승인됨", rejected: "반려됨", reviewed: "검토 완료", needs_review: "검토 대기"};
  const state = {token: "", principal: null, profiles: [], incidents: [], incident: null, documents: [], document: null, analysis: null, events: [], busy: false, loading: false, searching: false, documentLoading: false, auditLoading: false, version: 0, documentVersion: 0, profileReady: false, returnFocus: null};
  const savedKey = "trace-demo-session-v1";
  const readRequests = new Set();
  let sessionProbe = null;
  let sessionProbeToken = "";

  function node(tag, className, text) {
    const result = document.createElement(tag);
    if (className) result.className = className;
    if (text !== undefined && text !== null) result.textContent = String(text);
    return result;
  }
  function asArray(value) { return Array.isArray(value) ? value : []; }
  function string(value, fallback = "—") { return value === undefined || value === null || value === "" ? fallback : String(value); }
  function date(value) {
    if (!value) return "시각 없음";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return new Intl.DateTimeFormat("ko-KR", {month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23", timeZone: "UTC"}).format(parsed) + " UTC";
  }
  function badge(text) { return node("span", "badge", text); }
  function announce(text, tone = "") {
    $("notice").textContent = text;
    $("notice").className = "notice" + (tone ? " " + tone : "");
    $("notice").hidden = !text;
  }
  function cancelReads() {
    readRequests.forEach(controller => controller.abort());
    readRequests.clear();
  }
  function persistSession() {
    try {
      if (state.token && state.principal) sessionStorage.setItem(savedKey, JSON.stringify({token: state.token, principal: state.principal}));
      else sessionStorage.removeItem(savedKey);
    } catch (_) { /* Memory-only sessions remain usable when storage is blocked. */ }
  }
  function restoreSession() {
    try {
      const saved = JSON.parse(sessionStorage.getItem(savedKey) || "null");
      if (saved && typeof saved.token === "string" && saved.token && saved.principal && typeof saved.principal.site === "string" && typeof saved.principal.role === "string") {
        state.token = saved.token;
        state.principal = saved.principal;
      }
    } catch (_) { /* Ignore stale demo session storage. */ }
  }
  function clearSession() {
    cancelReads();
    state.version += 1;
    state.documentVersion += 1;
    state.loading = false;
    state.searching = false;
    state.documentLoading = false;
    state.auditLoading = false;
    state.token = "";
    state.principal = null;
    state.incidents = [];
    state.incident = null;
    state.documents = [];
    state.document = null;
    state.returnFocus = null;
    state.analysis = null;
    state.events = [];
    persistSession();
    renderPrincipal();
    renderIncidents();
    $("incident-workspace").hidden = true;
    $("welcome").hidden = false;
  }

  // Every valid profile can read incidents; use this safe read to distinguish a
  // backend 403 caused by expired identity from a role/site authorization denial.
  async function sessionIsValid(token) {
    if (sessionProbe && sessionProbeToken === token) return sessionProbe;
    sessionProbeToken = token;
    const pending = (async () => {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 10000);
      try {
        const response = await fetch("/api/incidents", {method:"GET", headers:{Accept:"application/json", Authorization:"Bearer " + token}, signal:controller.signal, credentials:"same-origin", cache:"no-store"});
        if (response.ok) return true;
        if (response.status === 401 || response.status === 403) return false;
        return null;
      } catch (_) { return null; }
      finally { clearTimeout(timer); }
    })();
    sessionProbe = pending;
    try { return await pending; }
    finally { if (sessionProbe === pending) { sessionProbe = null; sessionProbeToken = ""; } }
  }
  function expiredSession(token) {
    const error = new Error("데모 세션이 만료되었거나 유효하지 않습니다. 프로필을 선택하고 다시 접속해 주세요.");
    error.status = 401;
    if (state.token === token) { clearSession(); announce(error.message, "error"); }
    return error;
  }
  function moveTo(element, block = "start", focus = true) {
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    element.scrollIntoView({behavior: reduced ? "auto" : "smooth", block});
    if (focus) element.focus({preventScroll: true});
  }
  function returnToClaim() {
    let target = state.returnFocus;
    if (target && !target.isConnected && target.classList.contains("evidence-card")) {
      const documentId = target.dataset.documentId;
      target = documentId ? Array.from($("evidence-list").querySelectorAll(".evidence-card")).find(button => button.dataset.documentId === documentId) || null : null;
    }
    setTask(target && target.closest(".analysis-pane") ? "review" : "sources");
    if (target && target.isConnected) {
      if (target.closest(".source-picker")) target.closest(".source-picker").open = true;
      moveTo(target, "center");
    }
    else {
      setTask("sources");
      const picker = document.querySelector(".source-picker");
      picker.open = true;
      moveTo(picker.querySelector("summary"), "nearest");
    }
  }
  function setTask(task, focus = false) {
    if (!["cases","sources","review"].includes(task)) return;
    document.body.dataset.task = task;
    document.querySelectorAll(".task-tabs button").forEach(button => {
      const selected = button.dataset.task === task;
      button.setAttribute("aria-selected", String(selected));
      button.tabIndex = selected ? 0 : -1;
      if (selected && focus) button.focus();
    });
  }

  async function api(path, {method = "GET", body, timeout = 15000, authenticated = true} = {}) {
    const controller = new AbortController();
    if (method === "GET") readRequests.add(controller);
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeout);
    const requestToken = authenticated ? state.token : "";
    const headers = {"Accept": "application/json"};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (requestToken) headers.Authorization = "Bearer " + requestToken;
    try {
      const response = await fetch(path, {method, headers, body: body === undefined ? undefined : JSON.stringify(body), signal: controller.signal, credentials: "same-origin", cache: "no-store"});
      let data;
      try { data = await response.json(); }
      catch (_) { throw new Error("서버 응답을 읽을 수 없습니다. 연결 상태를 확인해 주세요."); }
      if (!response.ok) {
        if (response.status === 401 && requestToken) throw expiredSession(requestToken);
        if (response.status === 403 && requestToken) {
          const valid = await sessionIsValid(requestToken);
          if (valid === false) throw expiredSession(requestToken);
          // Preserve identity for a true ACL denial or an uncertain validation read.
        }
        const messages = {400: "입력 내용을 확인해 주세요.", 403: "현재 사이트 또는 역할에서 허용되지 않은 작업입니다.", 404: "접근 가능한 최신 근거 또는 사건을 찾을 수 없습니다.", 409: "현재 분석 상태에서는 요청한 작업을 완료할 수 없습니다.", 413: "요청 내용이 너무 깁니다.", 429: "서버가 다른 요청을 처리하고 있습니다. 잠시 뒤 다시 확인해 주세요.", 503: "분석 서비스를 사용할 수 없습니다."};
        const error = new Error(messages[response.status] || "서버에서 요청을 처리하지 못했습니다.");
        error.status = response.status;
        error.detail = typeof data.error === "string" ? data.error : "";
        throw error;
      }
      return data;
    } catch (error) {
      if (timedOut) {
        const wrapped = new Error(method === "GET" ? "근거·기록 조회 대기 시간이 초과되었습니다. 다시 조회해 주세요." : "응답 대기 시간이 초과되었습니다. 서버 처리는 계속될 수 있습니다. 감사 이력을 확인한 뒤 새 실행 여부를 판단해 주세요.");
        wrapped.timeout = true;
        throw wrapped;
      }
      if (error.name === "AbortError") throw error;
      if (error instanceof TypeError) throw new Error(method === "GET" ? "근거·기록 조회에 실패했습니다. 연결 상태를 확인해 주세요." : "요청의 저장 결과를 확인할 수 없습니다. 연결 상태와 감사 이력을 확인해 주세요.");
      throw error;
    } finally {
      clearTimeout(timer);
      readRequests.delete(controller);
    }
  }

  function showError(error) {
    if (error.name !== "AbortError") announce(error.message || "요청을 처리하지 못했습니다.", error.timeout ? "warn" : "error");
  }
  function reviewable(analysis) {
    return !!analysis && analysis.gate && analysis.gate.passed === true && analysis.mode !== "degraded" && !["failed", "degraded", "error"].includes(analysis.status);
  }
  function syncControls() {
    const pending = state.busy || state.loading;
    $("profile-select").disabled = pending || !state.profileReady;
    $("session-button").disabled = pending || !state.profileReady || !$("profile-select").value;
    $("session-button").textContent = state.token ? "프로필로 재접속" : "세션 시작";
    $("search-button").disabled = pending || state.searching || !state.incident;
    $("evidence-search").disabled = pending || !state.incident;
    $("analyze-button").disabled = pending || !state.incident || !state.token;
    $("analysis-question").disabled = pending || !state.incident;
    document.querySelectorAll('input[name="mode"]').forEach(input => { input.disabled = pending || !state.incident; });
    $("audit-refresh").disabled = pending || state.auditLoading || !state.incident;
    document.querySelectorAll(".incident-card").forEach(button => { button.disabled = pending; });
    document.querySelectorAll(".evidence-card,.source-ref,.citation-card").forEach(button => { button.disabled = state.documentLoading || state.loading; });
    const canReview = state.principal && state.principal.role === "reviewer" && state.analysis && !state.analysis.review;
    $("review-comment").disabled = pending || !canReview;
    $("approve-button").disabled = pending || !canReview || !reviewable(state.analysis);
    $("reject-button").disabled = pending || !canReview;
  }

  function renderPrincipal() {
    const target = $("principal");
    target.replaceChildren(node("span", "status-dot"), node("span", "", state.principal ? "사이트 " + state.principal.site + " / " + (roleLabels[state.principal.role] || state.principal.role) : "연결된 세션 없음"));
    $("role-help").textContent = state.principal ? (state.principal.role === "reviewer" ? "검토자: 인용 대조 후 승인·반려를 기록할 수 있습니다." : "읽기·분석 가능 / 승인·반려는 검토자 역할이 필요합니다.") + " 데모 로그인입니다." : "데모 로그인 · 기업 인증을 대체하지 않습니다.";
    syncControls();
  }
  function renderIncidents() {
    const list = $("incident-list");
    list.replaceChildren();
    $("incident-count").textContent = String(state.incidents.length);
    if (!state.incidents.length) {
      list.append(node("p", "empty-side", state.token ? "접근 가능한 사건이 없습니다." : "프로필을 선택하고 세션을 시작해 주세요."));
      return;
    }
    state.incidents.forEach(incident => {
      const button = node("button", "incident-card" + (state.incident && state.incident.id === incident.id ? " selected" : ""));
      button.type = "button";
      button.setAttribute("aria-current", state.incident && state.incident.id === incident.id ? "true" : "false");
      const top = node("div", "card-top");
      top.append(node("span", "", incident.id), node("span", "", "SITE " + incident.site));
      const bottom = node("div", "card-bottom");
      bottom.append(node("span", "", string(incident.service)), node("span", "", statusLabels[incident.status] || string(incident.status)));
      button.append(top, node("strong", "", incident.title), bottom);
      button.addEventListener("click", () => selectIncident(incident));
      list.append(button);
    });
    syncControls();
  }
  function renderIncident(incident, timeline) {
    $("incident-id").textContent = string(incident.id);
    $("incident-site").textContent = "SITE " + string(incident.site);
    $("incident-status").textContent = statusLabels[incident.status] || string(incident.status);
    $("incident-title").textContent = string(incident.title);
    $("incident-ticket").textContent = string(incident.ticket, "등록된 티켓 내용이 없습니다.");
    $("incident-service").textContent = string(incident.service);
    $("incident-time").textContent = date(incident.timestamp);
    const list = $("timeline");
    list.replaceChildren();
    if (!asArray(timeline).length) list.append(node("li", "muted", "접근 가능한 타임라인 기록이 없습니다."));
    asArray(timeline).forEach(event => {
      const item = node("li");
      const label = node("strong", "", string(event.title || event.text || event.action, "이벤트"));
      item.append(node("time", "", date(event.timestamp)), label);
      if (event.kind || event.document_id) item.append(node("p", "", [kindLabels[event.kind] || event.kind, event.revision === undefined ? "" : "rev." + event.revision, event.document_id].filter(Boolean).join(" · ")));
      if (event.description) item.append(node("p", "", event.description));
      list.append(item);
    });
  }
  function renderEvidence() {
    const list = $("evidence-list");
    list.replaceChildren();
    $("evidence-count").textContent = String(state.documents.length);
    if (!state.documents.length) list.append(node("p", "reasoning-empty", "검색 결과가 없거나 현재 역할에서 접근 가능한 근거가 없습니다."));
    state.documents.forEach(document => {
      const button = node("button", "evidence-card" + (state.document && state.document.id === document.id ? " selected" : ""));
      button.type = "button";
      button.dataset.documentId = document.id;
      button.setAttribute("aria-pressed", String(!!state.document && state.document.id === document.id));
      const top = node("div", "evidence-card-top");
      top.append(node("span", "", kindLabels[document.kind] || string(document.kind)), node("span", "", "rev." + string(document.revision)));
      const badges = node("div", "badge-row");
      badges.append(badge("SITE " + string(document.site)));
      asArray(document.roles).forEach(role => badges.append(badge(roleLabels[role] || role)));
      button.append(top, node("strong", "", document.title), badges);
      button.addEventListener("click", () => openDocument(document.id, "", undefined, button));
      list.append(button);
    });
    syncControls();
  }
  function renderDocument(document, quote = "") {
    $("document-view").hidden = !document;
    $("document-empty").hidden = !!document;
    $("return-claim").hidden = !document || !state.returnFocus;
    if (!document) return;
    $("document-kind").textContent = kindLabels[document.kind] || string(document.kind);
    $("document-revision").textContent = "rev." + string(document.revision);
    $("document-title").textContent = string(document.title);
    const badges = $("document-badges");
    badges.replaceChildren(badge("SITE " + string(document.site)));
    asArray(document.roles).forEach(role => badges.append(badge(roleLabels[role] || role)));
    badges.append(badge(date(document.timestamp)));
    $("document-ref").textContent = string(document.id) + " / " + string(document.logical_id) + " / 최신 접근 가능 개정";
    const content = string(document.content, "");
    $("document-content").replaceChildren();
    const start = quote ? content.indexOf(quote) : -1;
    if (start >= 0) {
      $("document-content").append(documentText(content.slice(0, start)), node("mark", "", quote), documentText(content.slice(start + quote.length)));
    } else $("document-content").textContent = content;
    $("citation-check").hidden = true;
    renderEvidence();
  }
  function documentText(value) { return document.createTextNode(value); }

  function renderReasoning(category, items, withRefs = true) {
    const list = $("" + category);
    list.replaceChildren();
    $("" + category + "-count").textContent = String(items.length);
    if (!items.length) {
      list.append(node("p", "reasoning-empty", category === "unknowns" ? "기록된 미확인 사항이 없습니다. 완전성이 보장되는 것은 아닙니다." : "이번 결과에 기록된 항목이 없습니다."));
      return;
    }
    items.forEach(item => {
      const card = node("div", "reasoning-item");
      card.append(node("p", "", typeof item === "string" ? item : string(item.text, "")));
      if (item && item.observation && typeof item.observation === "object") {
        const observed=item.observation;
        card.append(node("p","tiny muted",String(observed.entity)+" = "+String(observed.value)+" "+String(observed.unit)+" / 관측 "+date(observed.observed_at)));
      }
      if (withRefs && item && typeof item === "object") {
        const refs = node("div", "source-refs");
        asArray(item.source_ids).forEach(id => {
          const button = node("button", "source-ref", id);
          button.type = "button";
          button.setAttribute("aria-label", String(id) + " 근거 원문 확인");
          button.addEventListener("click", () => openDocument(id, "", undefined, button));
          refs.append(button);
        });
        if (!refs.children.length) refs.append(node("span", "tiny muted", "연결된 출처 없음"));
        card.append(refs);
      }
      list.append(card);
    });
  }
  function renderAnalysis() {
    const analysis = state.analysis;
    $("analysis-result").hidden = !analysis;
    $("analysis-empty").hidden = !!analysis || state.busy;
    const retrievalFailed = !!(analysis && analysis.metrics && analysis.metrics.failure_stage === "retrieval");
    $("analysis-mode-badge").textContent = retrievalFailed ? "근거 검색 실패 · 분석 제한" : analysis ? (modeLabels[analysis.mode] || string(analysis.mode)) : "분석 대기";
    if (!analysis) { syncControls(); return; }
    $("analysis-mode-badge").style.color = analysis.mode === "degraded" ? "var(--red)" : analysis.mode === "ollama" ? "var(--amber)" : "var(--teal)";
    $("analysis-summary").textContent = string(analysis.summary, "요약이 없습니다.");
    $("analysis-status").textContent = retrievalFailed ? "검색 실패" : analysis.review ? (analysis.review.decision === "approved" ? "승인됨" : analysis.review.decision === "rejected" ? "반려됨" : "검토 완료") : (statusLabels[analysis.status] || string(analysis.status));
    const metrics = analysis.metrics || {};
    const meta = [analysis.id];
    if (typeof metrics.duration_ms === "number") meta.push("처리 " + Math.round(metrics.duration_ms) + " ms");
    if (typeof metrics.latency_ms === "number") meta.push("처리 " + Math.round(metrics.latency_ms) + " ms");
    if (metrics.model) meta.push(String(metrics.model));
    if (metrics.model_task) meta.push("모델 역할: 정형 관측 추출");
    if (metrics.retrieval_error_kind) meta.push("검색 실패 유형: " + String(metrics.retrieval_error_kind));
    if (metrics.model_error_kind) meta.push("실패 유형: "+String(metrics.model_error_kind));
    if (typeof metrics.total_ms === "number" && typeof metrics.latency_ms !== "number") meta.push("처리 "+Math.round(metrics.total_ms)+" ms");
    $("analysis-meta").textContent = meta.filter(Boolean).join(" / ");
    const passed = reviewable(analysis);
    $("gate").className = "gate " + (passed ? "passed" : "failed");
    $("gate-symbol").textContent = passed ? "✓" : "!";
    $("gate-title").textContent = passed ? (analysis.review ? "인용·추출 검사 통과 · 검토 기록 있음" : "인용·추출 검사 통과 · 사람 검토 필요") : "인용·추출 검사 미통과 · 승인 차단";
    const issues = $("gate-issues");
    issues.replaceChildren();
    if (retrievalFailed) issues.append(node("li", "", "근거 검색에 실패하여 원문 관측을 확인할 수 없습니다. 모델 추출은 실행하지 않았으며 승인이 차단됩니다."));
    else if (analysis.mode === "degraded" || ["failed", "error", "degraded"].includes(analysis.status)) issues.append(node("li", "", "모델 추출·검증에 실패했거나 제한된 결과입니다. 이 분석은 승인할 수 없습니다."));
    if (!analysis.gate || typeof analysis.gate.passed !== "boolean") issues.append(node("li", "", "인용·추출 검사 상태를 확인할 수 없습니다."));
    asArray(analysis.gate && analysis.gate.issues).forEach(issue => issues.append(node("li", "", typeof issue === "string" ? issue : JSON.stringify(issue))));
    if (passed) issues.append(node("li", "", "출처 권한·최신 개정·원문 일치·정형 관측 추출을 검사했습니다. 인과 진단과 의미적 지지는 사람이 확인해야 합니다."));
    ["facts", "hypotheses", "counterevidence", "unknowns"].forEach(category => renderReasoning(category, asArray(analysis[category]), category !== "unknowns"));
    const citations = $("citations");
    citations.replaceChildren();
    asArray(analysis.citations).forEach((citation, index) => {
      const button = node("button", "citation-card");
      button.type = "button";
      const label = node("div", "citation-label");
      label.append(node("span", "", String(index + 1).padStart(2, "0")), node("span", "", string(citation.document_id) + " / rev." + string(citation.revision)), node("span", "", string(citation.title, "")));
      button.append(label, node("blockquote", "", string(citation.quote, "인용문 없음")));
      button.addEventListener("click", () => openDocument(citation.document_id, citation.quote, citation.revision, button));
      citations.append(button);
    });
    if (!asArray(analysis.citations).length) citations.append(node("p", "reasoning-empty", "인용된 원문이 없습니다."));
    renderReview();
    syncControls();
  }
  function renderReview() {
    const analysis = state.analysis;
    if (!analysis) return;
    const reviewer = state.principal && state.principal.role === "reviewer";
    $("review-role").textContent = reviewer ? "검토자 권한" : "읽기 권한";
    $("review-form").hidden = !!analysis.review;
    $("review-existing").hidden = !analysis.review;
    if (analysis.review) {
      const review = analysis.review;
      $("review-existing").replaceChildren(node("strong", "", (review.decision === "approved" ? "승인 기록됨" : review.decision === "rejected" ? "반려 기록됨" : "검토 기록 있음") + " · " + date(review.timestamp)));
      if (review.comment) $("review-existing").append(node("p", "", review.comment));
      if (review.reviewer_id || review.actor_id) $("review-existing").append(node("p", "tiny muted", "검토자 " + (review.reviewer_id || review.actor_id)));
      $("review-explanation").textContent = "이 분석에는 검토 결정이 이미 기록되어 있습니다. 같은 분석의 결정은 중복 생성되지 않습니다.";
    } else {
      $("review-explanation").textContent = !reviewer ? "현재 프로필은 원문 확인과 분석이 가능합니다. 결정 기록은 검토자 프로필로만 할 수 있습니다." : reviewable(analysis) ? "인용과 가설의 구분을 확인한 뒤 결정해 주세요. 근거 인용·추출 검사 통과가 분석의 정확성을 보장하지는 않습니다." : "승인이 차단되었습니다. 위 검증 사유를 확인하고, 검토 의견과 함께 반려할 수 있습니다.";
    }
    syncControls();
  }
  function renderAudit() {
    const list = $("audit-list");
    list.replaceChildren();
    $("audit-count").textContent = String(state.events.length);
    if (!state.events.length) list.append(node("p", "reasoning-empty", "현재 접근 범위에 기록된 감사 이력이 없습니다."));
    state.events.slice().reverse().forEach(event => {
      const item = node("div", "audit-event");
      const detail = node("div");
      const labels = {analysis_created: "분석 생성", analysis_reviewed: "검토 결정", review_created: "검토 결정"};
      detail.append(node("strong", "", labels[event.action] || string(event.action, "작업 기록")));
      const parts = [event.analysis_id, event.actor_id ? "담당 " + event.actor_id : "", event.mode ? (modeLabels[event.mode] || event.mode) : "", typeof event.gate_passed === "boolean" ? (event.gate_passed ? "인용·추출 검사 통과" : "검증 미통과") : ""];
      detail.append(node("p", "", parts.filter(Boolean).join(" · ")));
      if (event.comment) detail.append(node("p", "", event.comment));
      item.append(node("time", "", date(event.timestamp)), detail);
      if (event.decision) item.append(badge(event.decision === "approved" ? "승인" : event.decision === "rejected" ? "반려" : "검토 기록"));
      else if (event.analysis_id) {
        const button = node("button", "text-button", "분석 열기 ↗");
        button.type = "button";
        button.disabled = state.busy;
        button.addEventListener("click", () => openAnalysis(event.analysis_id));
        item.append(button);
      }
      list.append(item);
    });
  }

  async function loadProfiles() {
    try {
      const data = await api("/api/profiles", {authenticated: false});
      state.profiles = asArray(data.profiles);
      $("profile-select").replaceChildren();
      state.profiles.forEach(profile => {
        const option = node("option", "", string(profile.label, "사이트 " + profile.site + " / " + (roleLabels[profile.role] || profile.role)));
        option.value = profile.id;
        $("profile-select").append(option);
      });
      const defaultId = state.principal && state.principal.id ? state.principal.id : "A-it";
      if (state.profiles.some(profile => profile.id === defaultId)) $("profile-select").value = defaultId;
      state.profileReady = state.profiles.length > 0;
      if (!state.profileReady) announce("사용 가능한 데모 프로필이 없습니다.", "warn");
    } catch (error) { $("profile-select").replaceChildren(node("option", "", "프로필을 불러오지 못했습니다")); showError(error); }
    syncControls();
  }
  async function health() {
    try {
      const data = await api("/api/health", {authenticated: false});
      $("health-text").textContent = data.ok ? "로컬 워크벤치 연결됨" : "서버 상태 확인 필요";
      $("health-dot").style.background = data.ok ? "#90b89a" : "#d9b576";
      if (data.synthetic !== true) announce("합성 데이터 상태를 확인할 수 없습니다. 서버 설정을 확인해 주세요.", "warn");
    } catch (_) { $("health-text").textContent = "워크벤치 연결 실패"; $("health-dot").style.background = "#d38e79"; }
  }
  async function startSession() {
    if (state.busy || state.loading || !$("profile-select").value) return;
    state.loading = true;
    syncControls();
    announce("데모 세션에 접속하고 있습니다.");
    try {
      const data = await api("/api/session", {method: "POST", body: {profile: $("profile-select").value}, authenticated: false});
      if (typeof data.token !== "string" || !data.principal) throw new Error("세션 응답이 올바르지 않습니다.");
      clearSession();
      state.loading = true;
      state.token = data.token;
      state.principal = data.principal;
      persistSession();
      renderPrincipal();
      await loadIncidents();
    } catch (error) { showError(error); }
    finally { state.loading = false; syncControls(); }
  }
  async function loadIncidents() {
    const data = await api("/api/incidents");
    state.incidents = asArray(data.incidents);
    renderIncidents();
    if (state.incidents.length) await selectIncident(state.incidents[0], true);
    else announce("현재 사이트에 등록된 사건이 없습니다.", "warn");
  }
  async function selectIncident(incident, initial = false) {
    if (state.busy || (state.loading && !initial)) return;
    cancelReads();
    const version = ++state.version;
    state.documentVersion += 1;
    state.loading = true;
    state.incident = incident;
    state.returnFocus = null;
    setTask("sources");
    state.analysis = null;
    state.document = null;
    state.documents = [];
    state.events = [];
    $("evidence-search").value = "";
    $("analysis-question").value = "";
    $("review-comment").value = "";
    $("analysis-mode-badge").style.color = "";
    $("welcome").hidden = true;
    $("incident-workspace").hidden = false;
    renderIncidents();
    renderIncident(incident, []);
    renderEvidence();
    renderDocument(null);
    renderAnalysis();
    renderAudit();
    announce("사건과 접근 가능한 최신 근거를 불러오고 있습니다.");
    try {
      const results = await Promise.allSettled([
        api("/api/incidents/" + encodeURIComponent(incident.id)),
        api("/api/evidence?incident_id=" + encodeURIComponent(incident.id)),
        api("/api/audit?incident_id=" + encodeURIComponent(incident.id))
      ]);
      if (version !== state.version) return;
      const errors = [];
      if (results[0].status === "fulfilled") {
        state.incident = results[0].value.incident;
        renderIncident(state.incident, results[0].value.timeline);
      } else errors.push(results[0].reason);
      if (results[1].status === "fulfilled") { state.documents = asArray(results[1].value.documents); renderEvidence(); }
      else errors.push(results[1].reason);
      if (results[2].status === "fulfilled") { state.events = asArray(results[2].value.events); renderAudit(); }
      else errors.push(results[2].reason);
      if (errors.length) showError(errors.find(error => error.status === 401) || errors[0]);
      else announce("");
      if (state.documents.length && state.token) {
        state.document = state.documents[0];
        renderDocument(state.document);
      }
    } catch (error) { if (version === state.version) showError(error); }
    finally { if (version === state.version) { state.loading = false; renderIncidents(); syncControls(); } }
  }
  async function searchEvidence(event) {
    event.preventDefault();
    if (!state.incident || state.searching || state.busy || state.loading) return;
    const version = state.version;
    state.searching = true;
    syncControls();
    try {
      const data = await api("/api/evidence?incident_id=" + encodeURIComponent(state.incident.id) + "&q=" + encodeURIComponent($("evidence-search").value.trim()));
      if (version !== state.version) return;
      state.documents = asArray(data.documents);
      state.document = null;
      renderEvidence();
      renderDocument(null);
      announce(state.documents.length ? "" : "검색 결과가 없습니다. 다른 키워드를 입력해 주세요.", state.documents.length ? "" : "warn");
    } catch (error) { if (version === state.version) showError(error); }
    finally { state.searching = false; syncControls(); }
  }
  async function openDocument(id, quote = "", expectedRevision, origin = document.activeElement) {
    if (!id || state.documentLoading || state.loading) return;
    const version = state.version;
    const documentVersion = ++state.documentVersion;
    state.returnFocus = origin && origin !== document.body ? origin : null;
    state.documentLoading = true;
    state.document = null;
    renderDocument(null);
    renderEvidence();
    syncControls();
    try {
      const data = await api("/api/evidence/" + encodeURIComponent(id));
      if (version !== state.version || documentVersion !== state.documentVersion) return;
      state.document = data.document;
      renderDocument(state.document, typeof quote === "string" ? quote : "");
      if (quote) {
        $("citation-check").hidden = false;
        $("citation-check").className = "citation-check";
        $("citation-check").textContent = "원문 인용을 서버에서 검증하고 있습니다.";
        const checked = await api("/api/citations/" + encodeURIComponent(id) + "?quote=" + encodeURIComponent(quote));
        if (version !== state.version || documentVersion !== state.documentVersion) return;
        const citation = checked.citation;
        if (!citation || citation.document_id !== id || citation.quote !== quote || (expectedRevision !== undefined && citation.revision !== expectedRevision)) throw new Error("인용의 개정 또는 내용이 현재 근거와 일치하지 않습니다.");
        $("citation-check").textContent = "✓ 원문과 정확히 일치 · rev." + citation.revision;
      }
      setTask("sources");
      moveTo($("document-title"), "nearest");
    } catch (error) {
      if (version !== state.version || documentVersion !== state.documentVersion) return;
      if (quote && state.document && state.document.id === id) {
        $("citation-check").hidden = false;
        $("citation-check").className = "citation-check error";
        $("citation-check").textContent = "인용 검증 실패: " + error.message;
      }
      showError(error);
    } finally { state.documentLoading = false; syncControls(); }
  }
  async function analyze(event) {
    event.preventDefault();
    if (!state.incident || !state.token || state.busy || state.loading) return;
    const version = state.version;
    const mode = document.querySelector('input[name="mode"]:checked').value;
    state.busy = true;
    state.analysis = null;
    setTask("review");
    renderAnalysis();
    $("analysis-loading").hidden = false;
    $("analyze-button").firstElementChild.textContent = "분석 중…";
    syncControls();
    announce(mode === "model" ? "실제 로컬 모델 추론을 요청했습니다. 결과 또는 실패 상태를 기다리고 있습니다." : "규칙 기준선을 실행하고 있습니다. 이 경로는 모델 추론을 사용하지 않습니다.");
    try {
      const data = await api("/api/incidents/" + encodeURIComponent(state.incident.id) + "/analyze", {method: "POST", body: {mode, question: $("analysis-question").value.trim()}, timeout: 180000});
      if (version !== state.version) return;
      state.analysis = data.analysis;
      if (!state.analysis || !state.analysis.id) throw new Error("분석 응답이 올바르지 않습니다.");
      $("review-comment").value = "";
      renderAnalysis();
      const retrievalFailed = state.analysis.metrics && state.analysis.metrics.failure_stage === "retrieval";
      announce(retrievalFailed ? "근거 검색에 실패했습니다. 모델 추출을 실행하지 않았고 승인은 차단됩니다." : state.analysis.mode === "degraded" ? "모델 추출·검증에 실패했습니다. 검증 사유와 미확인 사항을 확인하세요. 승인은 차단됩니다." : "분석이 기록되었습니다. 인용을 원문과 대조한 뒤 검토하세요.", retrievalFailed || state.analysis.mode === "degraded" ? "warn" : "");
      await refreshAudit(true);
    } catch (error) { if (version === state.version) { showError(error); if (error.timeout) await refreshAudit(true); } }
    finally {
      state.busy = false;
      $("analysis-loading").hidden = true;
      $("analyze-button").firstElementChild.textContent = "분석 실행";
      renderAnalysis();
      renderAudit();
      syncControls();
    }
  }
  async function openAnalysis(id) {
    if (!id || state.busy || state.loading || !state.incident) return;
    const version = state.version;
    state.loading = true;
    syncControls();
    try {
      const data = await api("/api/analyses/" + encodeURIComponent(id));
      if (version !== state.version) return;
      if (!data.analysis || data.analysis.incident_id !== state.incident.id) throw new Error("현재 사건의 분석을 찾을 수 없습니다.");
      state.analysis = data.analysis;
      $("review-comment").value = "";
      renderAnalysis();
      announce("");
      setTask("review");
      moveTo($("analysis-result"), "start");
    } catch (error) { if (version === state.version) showError(error); }
    finally { state.loading = false; syncControls(); }
  }
  async function refreshAudit(quiet = false) {
    if (!state.incident || !state.token || state.auditLoading) return;
    const version = state.version;
    state.auditLoading = true;
    syncControls();
    try {
      const data = await api("/api/audit?incident_id=" + encodeURIComponent(state.incident.id));
      if (version !== state.version) return;
      state.events = asArray(data.events);
      renderAudit();
      if (!quiet) announce("감사 이력을 갱신했습니다.");
    } catch (error) { if (version === state.version && !quiet) showError(error); }
    finally { state.auditLoading = false; syncControls(); }
  }
  async function submitReview(decision) {
    if (state.busy || state.loading || !state.analysis || state.analysis.review || !state.principal || state.principal.role !== "reviewer") return;
    if (decision === "approved" && !reviewable(state.analysis)) { announce("근거 검증을 통과한 정상 분석만 승인할 수 있습니다.", "warn"); return; }
    const version = state.version;
    const analysisId = state.analysis.id;
    state.busy = true;
    syncControls();
    try {
      const data = await api("/api/analyses/" + encodeURIComponent(analysisId) + "/review", {method: "POST", body: {decision, comment: $("review-comment").value.trim()}});
      if (version !== state.version || !state.analysis || state.analysis.id !== analysisId) return;
      state.analysis.review = data.review;
      state.analysis.status = data.review.decision;
      renderAnalysis();
      announce(data.duplicate ? "이 분석의 기존 검토 결정을 표시했습니다. 새 감사 기록은 생성되지 않았습니다." : (decision === "approved" ? "승인" : "반려") + " 결정이 기록되었습니다.");
      await refreshAudit(true);
    } catch (error) {
      if (version === state.version) {
        showError(error);
        if (error.timeout) {
          try {
            const data = await api("/api/analyses/" + encodeURIComponent(analysisId));
            if (version === state.version) {
              state.analysis = data.analysis; renderAnalysis();
              announce(state.analysis && state.analysis.review ? "서버 조회에서 기존 검토 기록을 확인했습니다. 결정 요청을 다시 보내지 않았습니다." : "서버 조회에서 검토 기록을 아직 확인하지 못했습니다. 감사 이력을 확인한 뒤 재시도 여부를 판단해 주세요.", state.analysis && state.analysis.review ? "" : "warn");
              await refreshAudit(true);
            }
          } catch (_) { /* Never automatically repeat a mutation after timeout. */ }
        }
      }
    } finally { state.busy = false; renderAudit(); syncControls(); }
  }

  document.querySelectorAll(".task-tabs button").forEach(button => {
    button.addEventListener("click", () => setTask(button.dataset.task));
    button.addEventListener("keydown", event => {
      const tasks = ["cases", "sources", "review"];
      const current = tasks.indexOf(button.dataset.task);
      let next = current;
      if (event.key === "ArrowRight") next = (current + 1) % tasks.length;
      else if (event.key === "ArrowLeft") next = (current + 2) % tasks.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = 2;
      else return;
      event.preventDefault(); setTask(tasks[next], true);
    });
  });
  $("return-claim").addEventListener("click", returnToClaim);
  $("profile-select").addEventListener("change", syncControls);
  $("session-button").addEventListener("click", startSession);
  $("search-form").addEventListener("submit", searchEvidence);
  $("analysis-form").addEventListener("submit", analyze);
  $("audit-refresh").addEventListener("click", () => refreshAudit());
  $("review-form").addEventListener("submit", event => { event.preventDefault(); submitReview("approved"); });
  $("reject-button").addEventListener("click", () => submitReview("rejected"));
  document.querySelectorAll('input[name="mode"]').forEach(input => input.addEventListener("change", () => {
    $("mode-description").textContent = input.value === "model" ? "명시적으로 실행할 때만 로컬 모델을 호출합니다. 실패하면 승인이 차단됩니다." : "규칙 기반 결과는 실제 모델 추론 결과와 별도로 표시합니다.";
  }));
  restoreSession();
  renderPrincipal();
  Promise.allSettled([loadProfiles(), health()]).then(async () => {
    if (state.token) {
      state.loading = true;
      syncControls();
      try { await loadIncidents(); }
      catch (error) { showError(error); }
      finally { state.loading = false; syncControls(); }
    }
  });
})();

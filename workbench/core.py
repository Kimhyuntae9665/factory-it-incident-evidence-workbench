"""Synthetic incident evidence backend. No runtime tools or ground-truth access."""
from __future__ import annotations

import json
import math
import re
import secrets
import sqlite3
import threading
import time
import uuid
from collections import Counter
from pathlib import Path

ROLES = ("operator", "it", "reviewer")
MAX_QUESTION = 4000
MAX_COMMENT = 2000


def _id():
    return uuid.uuid4().hex


def _text(value, maximum, field):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError("Invalid " + field)
    return value


def _tokens(text):
    return set(re.findall(r"[\w-]+", text.lower()))


def _codes(text):
    # Keep numeric identifiers and recognize uppercase symbolic error codes.
    numeric = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]*\d[A-Za-z0-9_-]*\b", text)
    symbolic = re.findall(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b", text)
    return {code.lower() for code in numeric + symbolic}


def _grams(text):
    compact = re.sub(r"\s+", "", text.lower())[:16000]
    return Counter(compact[i:i + 3] for i in range(max(0, len(compact) - 2)))


def _cosine(a, b):
    denominator = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    return sum(v * b.get(k, 0) for k, v in a.items()) / denominator if denominator else 0.0


class Store:
    def __init__(self, corpus_path, db_path):
        data = json.loads(Path(corpus_path).read_text(encoding="utf-8"))
        self._incidents = {item["id"]: item for item in data["incidents"]}
        self._documents = {item["id"]: item for item in data["documents"]}
        if len(self._incidents) != len(data["incidents"]) or len(self._documents) != len(data["documents"]):
            raise ValueError("Duplicate corpus ID")
        self._latest = {}
        for document in self._documents.values():
            if not isinstance(document["revision"], int) or isinstance(document["revision"], bool):
                raise ValueError("Invalid revision")
            key = document["logical_id"]
            previous = self._latest.get(key)
            if previous is not None and previous["revision"] == document["revision"]:
                raise ValueError("Ambiguous latest revision")
            if previous is None or document["revision"] > previous["revision"]:
                self._latest[key] = document
        self._sessions = {}
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY, site TEXT NOT NULL, incident_id TEXT NOT NULL,
                source_ids TEXT NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews (
                analysis_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT, site TEXT NOT NULL,
                incident_id TEXT NOT NULL, analysis_id TEXT, payload TEXT NOT NULL);
        """)
        self._db.commit()

    def close(self):
        with self._lock:
            self._db.close()

    def profiles(self):
        return [{"id": site + "-" + role, "site": site, "role": role,
                 "label": site + " / " + role + " (synthetic demo login)"}
                for site in ("A", "B") for role in ROLES]

    def session(self, profile):
        principal = next((p for p in self.profiles() if p["id"] == profile), None)
        if principal is None:
            raise ValueError("Unknown demo profile")
        principal = {k: principal[k] for k in ("id", "site", "role")}
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions[token] = principal
        return {"token": token, "principal": dict(principal)}

    def principal(self, token):
        with self._lock:
            principal = self._sessions.get(token)
            if principal is None:
                raise PermissionError("Authentication required")
            return dict(principal)

    def _check_principal(self, principal):
        if not isinstance(principal, dict) or principal.get("id") != principal.get("site", "") + "-" + principal.get("role", ""):
            raise PermissionError("Invalid principal")
        if principal.get("site") not in ("A", "B") or principal.get("role") not in ROLES:
            raise PermissionError("Invalid principal")

    def incidents(self, principal):
        self._check_principal(principal)
        return [dict(item) for item in self._incidents.values() if item["site"] == principal["site"]]

    def _incident(self, principal, incident_id):
        self._check_principal(principal)
        incident = self._incidents.get(incident_id)
        if incident is None or incident["site"] != principal["site"]:
            raise KeyError("Incident not found")
        return incident

    def incident(self, principal, incident_id):
        incident = self._incident(principal, incident_id)
        timeline = [{"document_id": d["id"], "title": d["title"],
                     "timestamp": d["timestamp"], "kind": d["kind"], "revision": d["revision"]}
                    for d in self.evidence(principal, incident_id, limit=100)
                    if d.get("incident_id") == incident_id]
        timeline.sort(key=lambda item: (item["timestamp"], item["document_id"]))
        return {"incident": dict(incident), "timeline": timeline}

    def _accessible(self, principal, document):
        return (document["site"] == principal["site"]
                and principal["role"] in document["roles"]
                and self._latest.get(document["logical_id"], {}).get("id") == document["id"])

    def document(self, principal, doc_id):
        self._check_principal(principal)
        document = self._documents.get(doc_id)
        if document is None or not self._accessible(principal, document):
            raise KeyError("Evidence not found")
        linked_incident = document.get("incident_id")
        if linked_incident is not None:
            self._incident(principal, linked_incident)
        return dict(document)

    def evidence(self, principal, incident_id, query="", limit=6, *, ranking="token_overlap"):
        incident = self._incident(principal, incident_id)
        _text(query, MAX_QUESTION, "query")
        if not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("Invalid limit")
        if ranking not in ("token_overlap", "char3_plus_code"):
            raise ValueError("Invalid internal ranking method")
        candidates = [d for d in self._latest.values()
                      if self._accessible(principal, d)
                      and (d.get("incident_id") == incident_id
                           or (d.get("incident_id") is None and d["kind"] == "runbook"))]
        search = query + " " + incident["service"] + " " + incident["title"] + " " + incident["ticket"]
        terms = _tokens(search)
        codes = _codes(search) if ranking == "char3_plus_code" else set()
        grams = _grams(search) if ranking == "char3_plus_code" else Counter()
        def score(document):
            text = document["title"] + " " + document["content"]
            document_terms = _tokens(text)
            terms_match = len(terms & document_terms) / max(1, len(terms))
            code_match = len(codes & document_terms)
            same_case = 0.2 if document.get("incident_id") == incident_id else 0
            if ranking == "token_overlap":
                return terms_match + same_case
            return 3 * code_match + terms_match + _cosine(grams, _grams(text)) + same_case
        candidates.sort(key=lambda document: (-score(document), document["id"]))
        return [dict(document, retrieval_score=round(score(document), 6)) for document in candidates[:limit]]

    def citation(self, principal, doc_id, quote):
        document = self.document(principal, doc_id)
        _text(quote, 4000, "quote")
        if not quote or quote not in document["content"]:
            raise ValueError("Quote must be an exact evidence substring")
        return {"document_id": document["id"], "revision": document["revision"],
                "quote": quote, "title": document["title"]}

    def _baseline(self, incident, documents):
        from .rules import evidence_result
        result=evidence_result(documents)
        result["metrics"]["inference"]="deterministic observable baseline"
        return result

    def _validate_output(self, output, documents):
        issues = []
        allowed = {d["id"]: d for d in documents}
        if not isinstance(output, dict):
            output = {}
            issues.append("Invalid analysis object")
        summary = output.get("summary", "")
        if not isinstance(summary, str) or not summary or len(summary) > 10000:
            summary = "응답 형식 검증에 실패했습니다."
            issues.append("Invalid summary")
        result = {"summary": summary}
        from .rules import observed_facts
        expected_facts=observed_facts(documents)
        expected_typed={json.dumps(f["observation"],sort_keys=True,ensure_ascii=False):f for f in expected_facts}
        covered_typed=set()
        for field in ("facts", "hypotheses", "counterevidence"):
            items = output.get(field, [])
            clean = []
            if not isinstance(items, list) or len(items) > 40:
                items = []
                issues.append("Invalid " + field)
            for item in items:
                if (not isinstance(item, dict) or not isinstance(item.get("text"), str)
                        or not item["text"] or len(item["text"]) > 4000
                        or not isinstance(item.get("source_ids"), list)
                        or len(item["source_ids"]) > 20):
                    issues.append("Invalid " + field + " item")
                    continue
                ids = item["source_ids"]
                if any(not isinstance(source_id, str) or source_id not in allowed for source_id in ids):
                    issues.append("Unselected or inaccessible source")
                    continue
                if field == "facts" and not ids:
                    issues.append("Fact lacks evidence")
                    continue
                if field=="facts":
                    observation=item.get("observation")
                    canonical=json.dumps(observation,sort_keys=True,ensure_ascii=False) if isinstance(observation,dict) else None
                    expected=expected_typed.get(canonical)
                    if expected is None or item["text"]!=expected["text"] or ids!=expected["source_ids"]:
                        issues.append("Unsupported typed fact entity/value/polarity/time/text")
                        continue
                    covered_typed.add(canonical)
                    clean.append({"text":item["text"],"source_ids":list(ids),"observation":dict(observation)})
                else:
                    clean.append({"text": item["text"], "source_ids": list(dict.fromkeys(ids))})
            result[field] = clean
        if expected_typed and covered_typed!=set(expected_typed):issues.append("Important observed fact coverage incomplete")
        unknowns = output.get("unknowns", [])
        if not isinstance(unknowns, list) or len(unknowns) > 40 or any(not isinstance(x, str) or len(x) > 4000 for x in unknowns):
            unknowns = []
            issues.append("Invalid unknowns")
        result["unknowns"] = unknowns
        citations = output.get("citations", [])
        clean_citations = []
        if not isinstance(citations, list) or len(citations) > 40:
            citations = []
            issues.append("Invalid citations")
        for citation in citations:
            if not isinstance(citation, dict):
                issues.append("Invalid citation")
                continue
            doc_id = citation.get("document_id")
            document = allowed.get(doc_id) if isinstance(doc_id, str) else None
            quote = citation.get("quote")
            if (document is None or citation.get("revision") != document["revision"]
                    or not isinstance(citation.get("revision"), int) or isinstance(citation.get("revision"), bool)
                    or not isinstance(quote, str) or not quote or len(quote) > 4000
                    or quote not in document["content"]):
                issues.append("Invalid, stale, or inexact citation")
                continue
            clean_citations.append({"document_id": doc_id, "revision": document["revision"],
                                    "quote": quote, "title": document["title"]})
        if not clean_citations:
            issues.append("No verified citation")
        cited = {item["document_id"] for item in clean_citations}
        for field in ("facts", "hypotheses", "counterevidence"):
            if any(source not in cited for item in result[field] for source in item["source_ids"]):
                issues.append(field + " source lacks verified citation")
        result["citations"] = clean_citations
        metrics = output.get("metrics", {})
        # Only bounded scalar metrics are exposed; adapter metadata cannot override policy.
        result["metrics"] = {str(k)[:80]: v for k, v in list(metrics.items())[:30]
                             if isinstance(v, (str, int, float, bool)) and len(str(v)) <= 500
                             and (not isinstance(v, float) or math.isfinite(v))} if isinstance(metrics, dict) else {}
        result["gate"] = {"passed": not issues, "issues": list(dict.fromkeys(issues))}
        return result

    def _audit_event(self, principal, incident_id, analysis_id, action, **fields):
        event = {"id": _id(), "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "incident_id": incident_id, "analysis_id": analysis_id,
                 "actor_id": principal["id"], "action": action, **fields}
        self._db.execute("INSERT INTO audit(site,incident_id,analysis_id,payload) VALUES(?,?,?,?)",
                         (principal["site"], incident_id, analysis_id, json.dumps(event, ensure_ascii=False)))

    def analyze(self, principal, incident_id, question, mode="baseline"):
        incident = self._incident(principal, incident_id)
        _text(question, MAX_QUESTION, "question")
        if mode not in ("baseline", "model"):
            raise ValueError("Invalid analysis mode")
        started = time.perf_counter()
        retrieval_failed = False
        try:
            documents = self.evidence(principal, incident_id, question)
        except PermissionError:
            raise
        except (RuntimeError, OSError):
            # A retrieval infrastructure failure must never trigger inference.
            documents = []
            retrieval_failed = True
        retrieval_ms = (time.perf_counter() - started) * 1000
        inference_started = time.perf_counter()
        effective_mode = "baseline"
        degraded = False
        if retrieval_failed:
            effective_mode = "degraded"
            degraded = True
            raw = {"summary": "근거 검색을 사용할 수 없습니다. 검색 복구 후 다시 분석하세요.",
                   "facts": [], "hypotheses": [], "counterevidence": [],
                   "unknowns": ["검색 실패로 관측 근거를 확인할 수 없습니다."], "citations": [],
                   "metrics": {"failure_stage": "retrieval", "retrieval_error_kind": "retrieval_unavailable",
                               "requested_mode": mode}}
        elif mode == "baseline":
            raw = self._baseline(incident, documents)
        else:
            effective_mode = "ollama"
            try:
                from .llm import analyze_with_model
                raw = analyze_with_model(dict(incident), documents, question)
                if isinstance(raw, dict) and isinstance(raw.get("metrics"), dict) and raw["metrics"].get("mock") is True:
                    effective_mode = "mock"
            except (TimeoutError, RuntimeError, ImportError, OSError, ValueError) as error:
                raw = self._baseline(incident, documents)
                kind=str(error).split(":",1)[0]
                allowed_errors={"model_observation_entity_value_coverage_mismatch","model_incomplete_output","invalid_exact_quote","irrelevant_model_citation","inference_busy","inference_disabled_after_timeout","ollama_unavailable","ollama_http_400","no_accessible_evidence","no_typed_technical_evidence","question_budget_exceeded","evidence_budget_exceeded","invalid_output_structure","invalid_server_response","invalid_server_message","invalid_json_output","invalid_observation_structure"}
                raw["metrics"]["model_error_kind"]=kind if kind in allowed_errors else "model_failure"
                raw["metrics"]["requested_model"]="qwen3:4b"
                effective_mode = "degraded"
                degraded = True
        result = self._validate_output(raw, documents)
        if degraded:
            issue = ("Evidence retrieval unavailable; retry after retrieval recovers" if retrieval_failed
                     else "Model unavailable; degraded evidence baseline requires a fresh analysis")
            result["gate"] = {"passed": False, "issues": [issue]}
            if not retrieval_failed:
                result["unknowns"].append("모델 응답을 사용할 수 없어 근거 목록으로 대체했습니다.")
        result.update({"id": _id(), "incident_id": incident_id, "site": principal["site"],
                       "mode": effective_mode, "status": "degraded" if degraded else "needs_review",
                       "review": None})
        result["metrics"].update({"retrieval_method": "token_overlap",
                                  "retrieval_ms": round(retrieval_ms, 3),
                                  "inference_ms": 0.0 if retrieval_failed else round((time.perf_counter() - inference_started) * 1000, 3),
                                  "total_ms": round((time.perf_counter() - started) * 1000, 3),
                                  "evidence_count": len(documents), "synthetic": True})
        with self._lock:
            with self._db:
                self._db.execute("INSERT INTO analyses VALUES(?,?,?,?,?)",
                                 (result["id"], principal["site"], incident_id,
                                  json.dumps([d["id"] for d in documents]),
                                  json.dumps(result, ensure_ascii=False)))
                self._audit_event(principal, incident_id, result["id"], "analysis_created",
                                  mode=effective_mode, gate_passed=result["gate"]["passed"])
        return result

    def _analysis_row(self, principal, analysis_id):
        self._check_principal(principal)
        row = self._db.execute("SELECT site,incident_id,source_ids,payload FROM analyses WHERE id=?",
                               (analysis_id,)).fetchone()
        if row is None or row[0] != principal["site"]:
            raise KeyError("Analysis not found")
        self._incident(principal, row[1])
        for source_id in json.loads(row[2]):
            self.document(principal, source_id)
        return row

    def analysis(self, principal, analysis_id):
        with self._lock:
            row = self._analysis_row(principal, analysis_id)
            result = json.loads(row[3])
            review = self._db.execute("SELECT payload FROM reviews WHERE analysis_id=?", (analysis_id,)).fetchone()
            if review:
                result["review"] = json.loads(review[0])
                result["status"] = result["review"]["decision"]
                if principal["role"] == "operator":
                    result["status"] = "reviewed"
                    result["review"] = {"id": result["review"]["id"], "analysis_id": analysis_id,
                                        "timestamp": result["review"]["timestamp"]}
            return result

    def review(self, principal, analysis_id, decision, comment):
        self._check_principal(principal)
        if principal["role"] != "reviewer":
            raise PermissionError("Reviewer role required")
        if decision not in ("approved", "rejected"):
            raise ValueError("Invalid decision")
        _text(comment, MAX_COMMENT, "comment")
        with self._lock:
            with self._db:
                self._db.execute("BEGIN IMMEDIATE")
                row = self._analysis_row(principal, analysis_id)
                existing = self._db.execute("SELECT payload FROM reviews WHERE analysis_id=?", (analysis_id,)).fetchone()
                if existing:
                    return {"review": json.loads(existing[0]), "duplicate": True}
                analysis = json.loads(row[3])
                if decision == "approved" and (not analysis["gate"]["passed"] or analysis["mode"] == "degraded"):
                    raise ValueError("Cannot approve an analysis with a failed evidence gate")
                review = {"id": _id(), "analysis_id": analysis_id, "decision": decision,
                          "comment": comment, "reviewer_id": principal["id"],
                          "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                self._db.execute("INSERT INTO reviews VALUES(?,?)", (analysis_id, json.dumps(review, ensure_ascii=False)))
                self._audit_event(principal, row[1], analysis_id, "analysis_reviewed",
                                  decision=decision, comment=comment, reviewer_id=principal["id"])
                return {"review": review, "duplicate": False}

    def audit(self, principal, incident_id):
        self._incident(principal, incident_id)
        with self._lock:
            rows = self._db.execute("SELECT analysis_id,payload FROM audit WHERE site=? AND incident_id=? ORDER BY sequence",
                                    (principal["site"], incident_id)).fetchall()
            events = []
            for analysis_id, payload in rows:
                try:
                    if analysis_id:
                        self._analysis_row(principal, analysis_id)
                except KeyError:
                    continue
                event = json.loads(payload)
                if principal["role"] == "operator":
                    event = {k: v for k, v in event.items() if k not in ("decision", "comment", "reviewer_id")}
                    if event["action"] == "analysis_reviewed":
                        event.pop("actor_id", None)
                events.append(event)
            return events

"""Fixed synthetic CPU retrieval ranking checks; no generation or answer-key reads."""
import argparse
import hashlib
import json
import statistics
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from workbench.core import Store, _tokens, _codes, _grams, _cosine

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("token_overlap", "char3_plus_code")
BUDGETS = (3, 4, 6)
BYTE_BUDGET = 4096
REPEATS = 7


def candidate_pool(store, principal, incident_id):
    store._incident(principal, incident_id)
    return [d for d in store._latest.values()
            if store._accessible(principal, d)
            and (d.get("incident_id") == incident_id
                 or (d.get("incident_id") is None and d["kind"] == "runbook"))]


def token_ranking(store, principal, incident_id, query):
    incident = store._incident(principal, incident_id)
    terms = _tokens(query + " " + incident["service"] + " " + incident["title"] + " " + incident["ticket"])
    candidates = candidate_pool(store, principal, incident_id)
    def score(document):
        text = document["title"] + " " + document["content"]
        return len(terms & _tokens(text)) / max(1, len(terms)) + (0.2 if document.get("incident_id") == incident_id else 0)
    return sorted(candidates, key=lambda document: (-score(document), document["id"]))


def rank(store, principal, case, method):
    return store.evidence(principal, case["incident_id"], case["query"], limit=100, ranking=method)


def scored_ranking(store, principal, case, method, documents):
    incident = store._incident(principal, case["incident_id"])
    search = case["query"] + " " + incident["service"] + " " + incident["title"] + " " + incident["ticket"]
    terms = _tokens(search)
    codes = _codes(search)
    grams = _grams(search)
    result = []
    for position, document in enumerate(documents, 1):
        text = document["title"] + " " + document["content"]
        lexical = len(terms & _tokens(text)) / max(1, len(terms))
        prior = 0.2 if document.get("incident_id") == case["incident_id"] else 0
        code = 3 * len(codes & _tokens(text)) if method == "char3_plus_code" else 0
        char = _cosine(grams, _grams(text)) if method == "char3_plus_code" else 0
        total = lexical + prior + code + char
        assert round(total, 6) == document["retrieval_score"]
        result.append({"document_id": document["id"], "rank": position, "score": document["retrieval_score"],
                       "full_precision_score": total,
                       "components": {"token_overlap": lexical, "same_case_prior": prior,
                                      "code_boost": code, "char3_cosine": char}})
    return result


def bounded_selection(documents, count):
    selected = []
    used = 0
    for document in documents:
        if len(selected) == count:
            break
        size = len(document["content"].encode("utf-8"))
        if used + size > BYTE_BUDGET:
            continue
        selected.append(document)
        used += size
    return selected, used


def fixed_suite():
    suite = []
    # These are observable-span retrieval targets, not incident diagnosis labels.
    codes = {"001": "ORDER_OK", "002": "INV_CONNECT", "003": "INV_CONNECT", "004": "INV_TIMEOUT"}
    def required(incident):
        suffix = incident[-3:]
        return [
            {"logical_id": incident + "-log", "quote": "code=" + codes[suffix]},
            {"logical_id": incident + "-log", "quote": "duration_ms="},
            {"logical_id": incident + "-config", "quote": "expected_port=19082"},
            {"logical_id": incident + "-config", "quote": "timeout_ms=120"},
            {"logical_id": incident + "-health", "quote": "inventory process status=" + ("inactive" if suffix == "003" else "active")},
        ]
    def add(id, category, incident, query, spans):
        suite.append({"id": id, "category": category, "profile": "B-it", "incident_id": incident,
                      "query": query, "required_spans": spans})
    for suffix, code in codes.items():
        incident = "INC-B-" + suffix
        add("technical-" + suffix, "log_config_health_coverage", incident,
            code + " mes-orders inventory.endpoint expected_port timeout_ms inventory process status health duration_ms", required(incident))
    for suffix in ("002", "003", "004"):
        incident = "INC-B-" + suffix
        add("code-" + suffix, "digitless_error_code", incident, codes[suffix],
            [{"logical_id": incident + "-log", "quote": "code=" + codes[suffix]}])
    for suffix, kind, quote in (("002", "log", "code=INV_CONNECT"), ("002", "config", "expected_port=19082"),
                               ("004", "health", "inventory process status=active")):
        incident = "INC-B-" + suffix
        add("exact-id-" + kind, "exact_id", incident, incident + "-" + kind + "-r2",
            [{"logical_id": incident + "-" + kind, "document_id": incident + "-" + kind + "-r2", "quote": quote}])
    korean = {
        "001": "주문이 잘 조회되는지 기록과 설정 및 의존 서비스 상태를 함께 확인해 주세요.",
        "002": "재고 서비스 접속이 거부됐어요. 실제 접속 주소와 기준 포트, 프로세스 생존 여부를 비교해 주세요.",
        "003": "주문 조회가 연결 실패로 끝났어요. 주소 설정과 재고 서비스 실행 상태를 보여 주세요.",
        "004": "주문 조회가 오래 걸려 제한 시간에 걸렸어요. 처리 시간과 시간 제한, 서비스 상태를 확인해 주세요."}
    for suffix, query in korean.items():
        incident = "INC-B-" + suffix
        add("korean-" + suffix, "korean_paraphrase", incident, query, required(incident))
    for suffix in ("002", "004"):
        incident = "INC-B-" + suffix
        add("counter-" + suffix, "counterevidence", incident,
            "서비스 전체 단절 가설을 반박하는 상태 조회 근거 health HTTP200 inventory process status=active",
            [{"logical_id": incident + "-health", "quote": "inventory process status=active"},
             {"logical_id": incident + "-health", "quote": "health HTTP200"}])
    add("current-runbook", "latest_revision_positive", "INC-B-004",
        "RUN-B-r2 A timeout alone does not prove service failure",
        [{"logical_id": "RUN-B", "document_id": "RUN-B-r2", "quote": "A timeout alone does not prove service failure."}])
    return suite


def check_targets(suite, data):
    latest = {}
    for document in data["documents"]:
        previous = latest.get(document["logical_id"])
        if previous is None or document["revision"] > previous["revision"]:
            latest[document["logical_id"]] = document
    for case in suite:
        for target in case["required_spans"]:
            document = latest.get(target["logical_id"])
            if document is None or target["quote"] not in document["content"]:
                raise ValueError("Fixed suite target missing: " + case["id"])
            if target.get("document_id") and target["document_id"] != document["id"]:
                raise ValueError("Corpus revisions changed; revise fixed suite explicitly")


def measures(documents, targets, full_ranking):
    logical_ids = {d["logical_id"] for d in documents}
    required_ids = {t["logical_id"] for t in targets}
    covered = [any(d["logical_id"] == t["logical_id"] and t["quote"] in d["content"]
                   and (not t.get("document_id") or d["id"] == t["document_id"]) for d in documents) for t in targets]
    positions = [i + 1 for i, d in enumerate(full_ranking) if d["logical_id"] in required_ids]
    return {"document_recall": len(logical_ids & required_ids) / len(required_ids),
            "span_recall": sum(covered) / len(covered), "all_required_spans": all(covered),
            "mrr": 1 / min(positions) if positions else 0,
            "missing_spans": [target for target, ok in zip(targets, covered) if not ok]}


def negative_checks(store):
    checks = []
    cases = [
        ("cross_site_incident", "A-it", "INC-B-002", "INV_CONNECT", None),
        ("operator_restricted_log", "B-operator", "INC-B-002", "INV_CONNECT", "INC-B-002-log"),
        ("operator_restricted_config", "B-operator", "INC-B-002", "expected_port", "INC-B-002-config"),
        ("operator_restricted_health", "B-operator", "INC-B-002", "health", "INC-B-002-health"),
        ("cross_case", "B-it", "INC-B-001", "INV_CONNECT", "INC-B-002-log"),
    ]
    for method in METHODS:
        for name, profile, incident_id, query, prohibited_logical in cases:
            principal = store.session(profile)["principal"]
            denied = False
            documents = []
            try:
                documents = rank(store, principal, {"incident_id": incident_id, "query": query}, method)
            except KeyError:
                denied = True
            passed = denied if prohibited_logical is None else all(d["logical_id"] != prohibited_logical for d in documents)
            checks.append({"check": name, "method": method, "passed": passed})
        principal = store.session("B-it")["principal"]
        documents = rank(store, principal, {"incident_id": "INC-B-004", "query": "RUN-B-r1 obsolete"}, method)
        checks.append({"check": "no_obsolete_runbook", "method": method,
                       "passed": all(d["id"] != "RUN-B-r1" for d in documents)})
        documents = rank(store, principal, {"incident_id": "INC-B-002", "query": "INC-B-002-log-r1"}, method)
        checks.append({"check": "no_obsolete_incident_log", "method": method,
                       "passed": all(d["id"] != "INC-B-002-log-r1" for d in documents)})
    # Explicit latest-denied/old-allowed fixture: ranker cannot fall back to r1.
    incident = {"id": "acl-case", "site": "B", "title": "ACL check", "ticket": "INV_CONNECT",
                "service": "mes-orders", "timestamp": "2026-09-30T00:00:00Z", "status": "open"}
    old = {"id": "acl-old", "logical_id": "acl-log", "revision": 1, "site": "B",
           "roles": ["operator", "it", "reviewer"], "incident_id": "acl-case", "kind": "log",
           "title": "ACL log", "content": "code=INV_CONNECT", "timestamp": incident["timestamp"]}
    latest = dict(old, id="acl-latest", revision=2, roles=["it", "reviewer"])
    with tempfile.TemporaryDirectory() as temporary:
        corpus = Path(temporary) / "corpus.json"
        corpus.write_text(json.dumps({"incidents": [incident], "documents": [old, latest]}))
        shadow = Store(corpus, Path(temporary) / "evaluation.sqlite3")
        try:
            principal = shadow.session("B-operator")["principal"]
            for method in METHODS:
                result = rank(shadow, principal, {"incident_id": "acl-case", "query": "INV_CONNECT"}, method)
                checks.append({"check": "latest_denied_no_old_fallback", "method": method, "passed": result == []})
        finally:
            shadow.close()
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/corpus.json")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/retrieval-eval-v1")
    args = parser.parse_args()
    data = json.loads(args.corpus.read_text(encoding="utf-8"))
    suite = fixed_suite()
    check_targets(suite, data)
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(dir=args.output) as temporary:
        store = Store(args.corpus, Path(temporary) / "evaluation.sqlite3")
        try:
            for case in suite:
                principal = store.session(case["profile"])["principal"]
                expected_pool = {d["id"] for d in candidate_pool(store, principal, case["incident_id"])}
                for method in METHODS:
                    samples = []
                    for _ in range(REPEATS):
                        started = time.perf_counter()
                        documents = rank(store, principal, case, method)
                        samples.append((time.perf_counter() - started) * 1000)
                    if {d["id"] for d in documents} != expected_pool:
                        raise AssertionError("Candidate pool mismatch")
                    for k in BUDGETS:
                        selected, used = bounded_selection(documents, k)
                        results.append({"case_id": case["id"], "category": case["category"], "method": method,
                                        "k": k, "content_bytes": used, "ranking_ms_median": statistics.median(samples),
                                        "candidate_count": len(documents), "selected_ids": [d["id"] for d in selected],
                                        "ranked_ids": [d["id"] for d in documents],
                                        "ranked_documents": scored_ranking(store, principal, case, method, documents),
                                        **measures(selected, case["required_spans"], documents)})
            negatives = negative_checks(store)
        finally:
            store.close()
    grouped = defaultdict(list)
    for result in results:
        grouped[(result["category"], result["method"], result["k"])].append(result)
    aggregates = []
    for (category, method, k), rows in sorted(grouped.items()):
        aggregates.append({"category": category, "method": method, "k": k, "query_count": len(rows),
                           "document_recall_mean": statistics.mean(r["document_recall"] for r in rows),
                           "span_recall_mean": statistics.mean(r["span_recall"] for r in rows),
                           "all_spans_queries": sum(r["all_required_spans"] for r in rows),
                           "mrr_mean": statistics.mean(r["mrr"] for r in rows),
                           "ranking_ms_median": statistics.median(r["ranking_ms_median"] for r in rows)})
    summary = {"synthetic": True, "claim": "enterprise-workflow reproduction retrieval test",
               "generation_used": False, "model_accuracy_measured": False,
               "suite_version": 1, "query_count": len(suite), "methods": list(METHODS),
               "dataset_role": "observed_fixed_regression_not_new_holdout",
               "runtime_default": "token_overlap",
               "query_file": str(args.output / "suite.json"), "corpus_path": str(args.corpus),
               "gold_source": "fixed observable-span targets declared in scripts/retrieval_eval.py; no answer-key reads",
               "formulas": {"token_overlap": "|query_tokens intersect doc_tokens| / max(1,|query_tokens|) + 0.2*same_incident",
                            "char3_plus_code": "token_overlap + 3*|exact_code_tokens intersect doc_tokens| + cosine(char3(query_context),char3(title_content))",
                            "weights": {"token_overlap": 1, "same_incident": 0.2, "exact_code_token": 3, "char3_cosine": 1},
                            "ties": "ascending document_id", "returned_score_decimals": 6},
               "corpus_sha256": hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
               "core_sha256": hashlib.sha256((ROOT / "workbench/core.py").read_bytes()).hexdigest(),
               "controls": {"same_acl_latest_revision_candidates": True, "same_query_incident_context": True,
                            "same_indexed_fields": ["title", "content"], "same_case_prior": 0.2,
                            "document_budgets": list(BUDGETS), "content_utf8_byte_budget": BYTE_BUDGET,
                            "repeats": REPEATS, "primary_k": 3},
               "limitations": ["Small fixed previously observed synthetic corpus; no generalization or factory ROI claim.",
                               "Prefix spans duration_ms= and inventory process status= test field retrieval, not numeric fact verification.",
                               "Exact IDs are unindexed; this category exposes a current limitation.",
                               "No learned encoder, packages, downloads, model generation, or diagnosis labels.",
                               "No inference about end-to-end model accuracy from retrieval scores.",
                               "Latency is local CPU ranking, not model or user-perceived latency."],
               "negative_checks": negatives, "negative_passed": sum(x["passed"] for x in negatives),
               "negative_total": len(negatives), "aggregates": aggregates, "results": results}
    failure_case_ids = ("technical-002", "korean-004", "exact-id-config")
    failure_examples = [{"case": next(case for case in suite if case["id"] == case_id),
                         "methods": [result for result in results if result["case_id"] == case_id and result["k"] == 3]}
                        for case_id in failure_case_ids]
    (args.output / "failure-examples.json").write_text(json.dumps(failure_examples, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "suite.json").write_text(json.dumps(suite, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Fixed synthetic retrieval comparison", "",
             "Enterprise-workflow reproduction test. CPU ranking only; no generation or model accuracy measurement.",
             "", "Shared ACL, latest revisions, queries, title/content index, case prior, top-k, and 4096-byte content budget.",
             "Primary k=3. The k=4/6 rows are budget sensitivity checks, not combined headline scores.",
             "Runtime default: token_overlap; hybrid comparison requires an explicit internal option.",
             "L=normalized token intersection, P=0.2 for same-incident documents, C=exact code-token count, G=char3 cosine.",
             "Token score=L+P; hybrid score=L+P+3*C+G. Ties use ascending document ID.",
             "Query/gold span targets: suite.json (declared in fixed_suite); source: data/corpus.json.",
             "Three failures with exact score components/ranks: failure-examples.json.",
             "Observed fixed regression/tuning corpus; no new independent holdout has been evaluated.",
             "", "| Category | Method | k | Queries | Doc recall | Span recall | All spans | MRR | CPU ms |",
             "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in aggregates:
        lines.append("| {category} | {method} | {k} | {query_count} | {document_recall_mean:.3f} | {span_recall_mean:.3f} | {all_spans_queries} | {mrr_mean:.3f} | {ranking_ms_median:.3f} |".format(**row))
    lines += ["", "ACL/revision negatives: %s/%s passed, reported separately." % (summary["negative_passed"], summary["negative_total"]),
              "", "Exact-ID queries target document IDs absent from the indexed fields. Missing results are retained.",
              "At k=6 most candidate pools are fully included, so high coverage is a budget result rather than strong ranking evidence.",
              "Current code boost can prioritize code-bearing tickets/runbooks over configuration/health at tight budgets.",
              "Small fixed previously observed corpus; no independent generalization, diagnosis, factory ROI, or model-quality claim."]
    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"query_count": len(suite), "negative_passed": summary["negative_passed"],
                      "negative_total": summary["negative_total"], "output": str(args.output),
                      "primary": [a for a in aggregates if a["k"] == 3]}, ensure_ascii=True))
    if summary["negative_passed"] != summary["negative_total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

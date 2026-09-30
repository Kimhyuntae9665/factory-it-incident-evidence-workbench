# Evaluation manifest

Calibration incidents: INC-A-001 through INC-A-004. Fixed heldout incidents: INC-B-001 through INC-B-004. Truth is stored only in evaluations/fixed_expected.json (or regenerated artifacts/heldout_expected.json; evaluator only); runtime never imports it. Eight cases are a small synthetic engineering test and cannot support real-factory ROI or MTTR claims.

Deterministic tests use adapter mocks and are labelled separately from real Ollama requests. Required gates: keyword baseline; latest revision without stale fallback; cross-site list/detail/citation/analysis ACL; untrusted instruction source; absent evidence abstention; timeouts and degraded retrieval; idempotent and concurrent human review; exact original citation.

Real checks record request/response, installed model, context, latency, output token count and process resource snapshots in artifacts/. Four readiness dimensions: Korean output, meaningful evidence citation, unsupported-answer abstention, structured JSON extraction. Context overflow rejection is separate. Semantic quality must not be inferred from HTTP status or valid JSON alone.

Compare the same authorized corpus using keyword baseline and CPU retrieval/model output. CAG comparison is deferred until a small same-corpus baseline exists. No measured cache hit, no CAG completion claim.

External RCAEval 12–20-case generalization evaluation is deferred until this first flow is working; no large benchmark stack installed.

The initial fixed B cases have now been observed during evaluation. Final extraction-v2 results are labelled fixed regression, not fresh heldout generalization. Cause labels are deterministic rules. New external cases require separate untouched split and exclusion of truth-bearing metadata. Simulator revisions preserve initial corpus and observations.

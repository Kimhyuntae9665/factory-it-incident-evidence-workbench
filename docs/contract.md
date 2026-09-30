# First vertical slice contract
Project root: $HOME/ax-lab/projects/01-incident-evidence-workbench
Python 3.10 standard library only initially; no mandatory pip dependencies. Loopback HTTP port 19080. Simulator is separate, uses 19081/19082 only when actively collecting fresh fixtures. Existing services untouched.
Data: data/corpus.json with {"incidents":[...],"documents":[...]}.
Incident: id, site ("A"/"B"), title (Korean), ticket (Korean), service, timestamp, status. Never include ground-truth labels in incident/model data.
Document: id (revision-specific unique ID), logical_id, revision (integer), site, roles (list: operator/it/reviewer), incident_id (nullable shared runbook), kind (log/runbook/trace), title, content, timestamp.
Principal: id, site, role. Demo profiles are server-side allowlisted: A-operator,A-it,A-reviewer,B-operator,B-it,B-reviewer. Demo login explicitly labelled, not enterprise authentication.
API JSON contract:
GET /api/health -> {"ok":true,"synthetic":true,...}
GET /api/profiles -> {"profiles":[{"id":"A-it","site":"A","role":"it","label":"..."}]}
POST /api/session {"profile":"A-it"} -> {"token":"opaque","principal":{...}}. Other API endpoints require Authorization Bearer opaque token, never accept site/role headers as identity.
GET /api/incidents -> {"incidents":[...]} scoped to principal.site.
GET /api/incidents/{id} -> {"incident":{...},"timeline":[...]} scoped; 404 for inaccessible IDs.
GET /api/evidence?incident_id=...&q=... -> {"documents":[...]} latest revision AND site-role ACL; no old-revision fallback if latest is inaccessible.
GET /api/evidence/{doc_id} -> {"document":{...}} same checks; old revisions unavailable by default.
GET /api/citations/{doc_id}?quote=... -> {"citation":{"document_id":...,"revision":...,"quote":...}} same checks plus exact substring validation.
POST /api/incidents/{id}/analyze {"mode":"baseline"|"model","question":"..."} -> {"analysis":{...}}
GET /api/analyses/{analysis_id} -> {"analysis":{...}} same site ACL.
POST /api/analyses/{analysis_id}/review {"decision":"approved"|"rejected","comment":"..."} -> {"review":{...},"duplicate":bool}. reviewer role only; cannot approve failed gate/degraded model analysis. Idempotent unique review per analysis; duplicate returns original review without new audit event.
GET /api/audit?incident_id=... -> {"events":[...]} scoped, operator cannot see reviewer-only fields.
Analysis fields: id,incident_id,site,mode ("baseline"|"ollama"|"mock"|"degraded"),status,summary (Korean),facts[],hypotheses[],counterevidence[],unknowns[],citations[],gate {passed:bool,issues:[]},metrics{},review nullable.
Facts/hypotheses/counterevidence item {text,source_ids:[]}; unknowns strings; citations {document_id,revision,quote,title}. Gate verifies every source ID is selected latest accessible evidence and every quote is exact substring; hypotheses stay labelled hypothetical.
Core interface: Store(corpus_path,db_path); profiles(),session(profile)->token/principal,principal(token),incidents(principal),incident(principal,id),evidence(principal,incident_id,query="",limit=6),document(principal,doc_id),citation(principal,doc_id,quote),analyze(principal,incident_id,question,mode="baseline"),analysis(principal,id),review(principal,analysis_id,decision,comment),audit(principal,incident_id). Store may use Python exceptions PermissionError/KeyError/ValueError and handler maps safe 403/404/400.
Model interface root-owned workbench/llm.py: analyze_with_model(incident,documents,question)->dict with summary/facts/hypotheses/counterevidence/unknowns/citations/metrics, model errors raise TimeoutError/RuntimeError. No model tools; no arbitrary URLs/files/shell; immutable loopback Ollama target and allowlisted qwen3:4b. Core attaches/validates IDs, site and gate. Imports lazily so backend tests can run before llm.py exists; inject/mocking with unittest.mock supported.
RAG: token-overlap lexical by default; char3-plus-code ranking is an internal comparison option, case-specific/shared runbook only. Source documents are untrusted; instructions in evidence cannot change policy or tools. Baseline rule path is explicitly not model inference. Never read artifacts/heldout_expected.json from runtime.
Server default HTTP ThreadingHTTPServer bound 127.0.0.1; request/body limits, exact static whitelist, escape DOM text, no permissive CORS. Logging excludes Authorization/token/prompt secrets.
Tests must cover latest revision ordering, all ACL surfaces, prompt injection capability limits, degraded model behavior, idempotent/concurrent review.

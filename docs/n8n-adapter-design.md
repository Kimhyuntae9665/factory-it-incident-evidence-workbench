# n8n orchestration adapter — design only

Status: design reference; no n8n installation, imported workflow, credential, external account connection or active automation. Current backend and UI remain the running implementation.

These are community templates hosted in the official n8n gallery. Their external-model and connector assumptions are not automatically compatible with this local project.

| Reference | Pattern to consider | Workbench adaptation |
|---|---|---|
| [On-prem KB RAG](https://n8n.io/workflows/13422-implement-on-prem-rag-with-qdrant-and-ollama-for-a-self-hosted-kb/) | Separate registration from querying | Keep evidence registration/revision validation separate from permission-scoped querying. Existing CPU lexical/ngram retrieval remains. No Qdrant or embedding installation. 7–8B examples and 768 dimensions must not be copied to the measured4B text model. |
| [Ticket triage](https://n8n.io/workflows/19465-triage-and-route-ai-powered-support-tickets-with-google-gemini-trello-and-gmail/) | Intake, classification, approval and routing | Normalize synthetic intake, request a backend analysis, and point a human to the workbench review UI. No Gmail/Trello/Gemini calls. |
| [Document comparison](https://n8n.io/workflows/7662-automated-document-compliance-validation-with-ai-and-vector-database/) | SOP retrieval and difference checks | Compare current authorized revisions and exact spans as review candidates. No automatic compliance judgment; confidence/retrieval scores are not calibrated probabilities. |
| [Postmortem tracking](https://n8n.io/workflows/18513-draft-and-track-incident-postmortems-with-openai-google-sheets-discord-and-gmail/) | Draft report and follow-up tracking | Derive a local draft from timeline, typed facts, provisional hypotheses, unknowns and audit decisions. No external publication or messages. |
| [Incident log correlation](https://n8n.io/workflows/14044-analyze-logs-and-correlate-incidents-with-openai-and-slack/) | Incident intake, bounded window collection, normalization, grouping and change correlation | Reuse the case/time-window evidence contract and timeline view; observe configuration/deployment relationships as correlations. Do not establish causality from temporal proximity. No OpenAI/Slack/vector-store execution. |

## Responsibility boundary

Backend owns site/role authorization, current revision selection, ingestion provenance, evidence schema, original spans, typed entity/value/polarity/time/coverage checks, bounded model extraction, provisional rules, approval gate and audit persistence. n8n may later coordinate collection requests, wait for backend human decisions and connect approved follow-up systems. It must not decide access or override failed analysis gates.

Current synthetic demo profiles are not suitable service credentials. A future adapter needs a separate server-minted, site-scoped read-only principal; this is a proposed capability and has NOT been added. Secrets belong in an approved credential mechanism, never workflow JSON, source text, model prompts or evidence.

Human approval stays in the backend review UI. An observer adapter does not receive reviewer rights. It consumes the recorded decision by analysis ID; a correlation ID is not approval authority. Revision/site/role are rechecked on every read. Prior approvals cannot authorize a revised source snapshot.

## Proposed collection envelope

This JSON illustrates a contract, not an implemented endpoint or external trigger:

```json
{
  "schema_version": 1,
  "correlation_id": "synthetic-event-001",
  "site": "A",
  "incident_id": "INC-A-002",
  "service": "mes-orders",
  "window": {
    "start": "2026-09-30T07:00:00Z",
    "end": "2026-09-30T07:15:00Z"
  },
  "modalities": {
    "logs": true,
    "metrics": false,
    "deployments": false,
    "configuration": true,
    "flags": false
  },
  "source_refs": ["INC-A-002-log-r2", "INC-A-002-config-r2"]
}
```

The backend derives the actual principal from authorization; supplied site and source IDs never grant access. A source must bind service/entity, observed timestamp/timezone, original span, immutable revision and ingestion origin. Missing modalities are explicit unknowns. The MVP has MES logs/configuration/health evidence, not real deployment/flag streams.

Evidence timelines may group similar error signatures and show nearby changes as provisional correlation annotations. No automatic remediation or fabricated root-cause label is permitted. Root-cause truth and injection metadata remain evaluation-only and unavailable to retrieval/model prompts.

## Proposed adapter state machine

received → normalized → permission-scoped evidence read → backend extraction/gate → awaiting human review → approved/rejected/degraded → local follow-up draft.

Persist event ID plus analysis ID and source revision digest for idempotency. Retry safe reads only; an uncertain mutation result must be reconciled by its existing ID before any repeated action. Backend review is already idempotent. A timeout/degraded gate remains visible; n8n cannot relabel it successful.

The future adapter should use the existing read surfaces where sufficient. A paginated audit cursor/event API and ingestion API are design proposals only. They require bounded input, provenance checks and authorization before implementation. No such new route is advertised as available today.

## Future acceptance checks

Use only synthetic local fixtures initially. Check duplicate events/approval, denied cross-site sources, stale revision after approval, missing modalities, injected log instructions, timeout/recovery and temporal correlation without causal certainty. Confirm the adapter sends no evidence to an external model or connector during dry runs.

Implementation remains deferred to a later approved development cycle. This document does not claim n8n integration or template execution.

# First implementation checkpoint

Scope: isolated remote project $HOME/ax-lab/projects/01-incident-evidence-workbench. All implementation and tests ran on the designated GPU host. No public deployment, model download, driver/VPN/firewall/authentication change or prior-workload shutdown.

Completed vertical flow:
- Separate loopback simulator observes actual MES order requests and inventory health probes. Eight cases across A/B sites; 70 revision-preserving documents after a second observed run. Initial revision and raw evidence are preserved in artifacts/corpus-v1.json and simulator-observations-v1.json.
- Read-only allowlisted evidence API, latest-revision-before-ACL list/detail/span/analysis checks, CPU lexical and character-ngram retrieval.
- Typed observations bind entity, scalar value, unit, polarity, observation timestamp, document, revision and original span. Canonical display text and complete selected technical-field coverage are validated separately from source/span existence.
- Rule baseline supplies provisional causal hypotheses and counterevidence. Model path uses existing qwen3:4b for typed observation extraction only. No claim of independent model causal diagnosis.
- Korean original-evidence/timeline/facts/hypotheses/counterevidence/unknowns UI, human review and scoped SQLite audit. Human review executes no remediation.
- Timeout degrades safely; no retry; single-thread and cross-process nonblocking inference lease. Process-local timeout latch requires verifying completion before app restart.
- Native-sandbox Chrome verifies the real UI. Headless browser uses no GPU and no downloaded browser package.

Measured model evidence:
- Schema readiness: Korean, citation, unsupported-answer abstention and JSON extraction all pass; strict 4096 context overflow rejects HTTP400. The citation test was corrected to inspect the separate source_ids field instead of requiring the same ID inside answer.
- Natural-language think:false /no_think remains unsuitable. Installed template SHA256 2d54db2b9bb29ce7db54fea63a891f5859603813c555b1f88b5e0994652897f9 matches the published 2d54 variant prefix. Installed model digest359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7. Render-only false and true both end assistant <think>; manual /no_think with false does not change the prefix. No tag/template update.
- Free model classification initial fixed cases:0/4; results degrade and cannot be approved.
- Final narrower model extraction fixed regression:4/4, baseline4/4; latency2.582–4.368s; peak whole-GPU3451MiB; minimum MemAvailable26321620KiB. Provisional causal labels are rules, not model accuracy. Cases were previously observed and are not independent generalization evidence.
- Already-installed qwen2.5-coder:7b one diagnostic fit reached5111MiB, cold request66.94s and wrong category. It is not selected; project default remains qwen3:4b.

Known limits:
- Synthetic demo profiles are not enterprise SSO.
- Only the configured observable schema has deterministic semantic support checks; arbitrary prose/inferences require human assessment.
- No independent model diagnosis, real factory validation, ROI/MTTR claim, CAG cache-hit evidence or external benchmark completion.
- RCAEval selective12–20-case evaluation remains deferred; no multi-GB dataset or heavy benchmark installation.

Final verification at 2026-09-30 07:25UTC:
37 deterministic tests passed in10.964s, including process-lease contention and hostile Host.
Real Chrome profile A-reviewer selected INC-A-002, baseline approval/audit, actual Qwen3 typed extraction(7facts,4.285s), rev.2 exact span highlight all passed. Mobile horizontal overflow false. Final security source review found no remaining high/medium issues.
The new application remains loopback127.0.0.1:19080; artifacts/app.pid records the owned PID.

User steering: n8n official templates are being researched by the parent-side researcher. No n8n installation or rewrite. Compare it later as an external collection/approval/connector automation candidate; source evidence is pending.

Five parent-selected n8n community references were checked; design-only adapter contract and responsibility boundary recorded in docs/n8n-adapter-design.md. No installation, external call, workflow activation or backend capability change.

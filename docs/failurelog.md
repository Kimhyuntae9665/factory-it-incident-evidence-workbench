# Failure log

2026-09-30: initial Ollama cold request client timeout canceled loading; no confirmed CUDA or OOM failure. Later loading worked without driver changes or downloads.

2026-09-30: qwen3:4b alias is Thinking 2507 internally. Ordinary think:false /no_think response leaked English reasoning into content; Korean, citation and abstention readiness failed. Exact JSON extraction was the only initial pass.

2026-09-30: request-only raw empty-think prefill did not repair the three natural language checks. Server model/template was not changed.

2026-09-30: schema readiness produced Korean and abstention content, but citation answer omitted the approving role and JSON omitted source S1. This is partial recovery, not complete readiness. Malformed invented source/quote values are rejected by project validators.

2026-09-30: first real incident analysis exhausted 512 output tokens and was rejected as model_incomplete_output. Subsequent tighter schema and exact quote choices are being evaluated. Actual response traces are preserved.

Final bounded extraction path passes4/4 fixed synthetic regression cases. Independent free classification remained0/4. The classification response may attach a real quote to a wrong category; typed extraction and contradiction/coverage gates separate these dimensions. Operator status leak and malformed-response errors identified by security review were fixed and regression tested.

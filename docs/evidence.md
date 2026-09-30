# Demand evidence and evaluation scope

The parent research selected incident evidence workbench after the initial one-hour research window. Supplied references:
- Bosch manufacturing production support: https://www.bosch.com/stories/agentic-ai-manufacturing-production/
- MakinaRocks role: https://makinarocks.career.greetinghr.com/ko/o/238056
- DeepAuto role: https://deepauto-ai.career.greetinghr.com/ko/o/209187

These motivate a reproducible synthetic enterprise IT exercise. They do not prove performance on actual factory data.

Installed model alias qwen3:4b internally identifies Qwen3 4B Thinking 2507. Ordinary think:false/no_think and request-only empty-think prefilling did not eliminate reasoning in content; HTTP200 alone failed the initial readiness checks. Schema-constrained JSON is under evaluation, not a proof that the thinking-only model has been converted to a non-thinking model.
Official model background:
https://huggingface.co/Qwen/Qwen3-4B-Thinking-2507
https://github.com/ollama/ollama/blob/v0.17.7/api/types.go
https://github.com/ollama/ollama/blob/v0.17.7/server/prompt.go

Deferred external evaluation candidate supplied by parent:
RCAEval https://github.com/phamquiluan/RCAEval and https://arxiv.org/html/2412.17015v2
After synthetic vertical flow passes, consider 12–20 selectively downloaded microservice cases. Verify modality and licensing at selection time. Exclude root-cause labels, injection times and filenames that reveal truth from retrieval. Root-cause entity labels do not supply complete citation ground truth. These are not actual MES/factory labels. No external dataset downloaded.

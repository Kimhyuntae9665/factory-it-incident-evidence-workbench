# Architecture

Separate simulator processes serve synthetic inventory and MES order reads on 127.0.0.1:19082 and :19081. Generation shuts down only these owned temporary servers. Eight observed cases across synthetic sites A and B represent normal reads, incorrect endpoint, unavailable dependency, and timeout with healthy dependency. Dataset errors remain useful counterevidence.

Application uses standard-library HTTP and SQLite. Demo profile selection mints opaque bearer sessions. Every incident, evidence list/detail, citation, stored analysis and audit query rechecks site and role. Current revision is selected BEFORE role filtering; inaccessible current revisions never fall back to stale documents. Stored model summaries must not leak IT-only sources to operators.

Retrieval uses lexical service/error matching and character n-grams on CPU. Retrieved source text is untrusted. Model receives selected authorized source documents only; no shell, Docker socket, API write tools, answer files or production data.

Localhost Ollama request is bounded, serialized, schema constrained, no tools, truncate:false and shift:false. Model output is independently validated against selected sources and exact original quote substrings. Unsupported/incomplete/timeout output degrades to retrieval evidence with a failed approval gate. Human review persists a separate unique decision with audit events and duplicate handling.

Threat boundaries: this is a single-host synthetic demo, not enterprise identity assurance. Host administrators can inspect demo corpus. Prompt injection cannot execute tools; semantic hallucination still needs heldout evaluation and human review.

CAG is deferred. keep_alive residence is not evidence of prefix cache hits; installed Ollama 0.17.7 does not expose prompt_eval_cached_count. No cache performance claim is made.

Current MVP model role is typed observation extraction. Every extracted scalar/null must match deterministic CPU observations. Facts require canonical entity/value/unit/polarity/time/source/revision/span/text and important-field coverage. Rules supply provisional causal hypotheses. The UI claims citation/extraction checks only; general semantic entailment and diagnosis remain human review.

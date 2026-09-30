# Runbook

Use README commands from the isolated project. All new listeners must bind 127.0.0.1. No service, firewall, driver, VPN, Docker or existing model configuration change is required.

Before a live inference: inspect nvidia-smi compute applications and Ollama /api/ps; avoid overlap with unrelated jobs. Use only the existing qwen3:4b model and a single bounded request. Artifact traces contain synthetic evidence and no credentials.

On model timeout: app latches inference disabled, prevents another request and shows degraded evidence. Verify the owned request has ended using Ollama process/log observations before restarting ONLY this project process. Never stop unrelated Ollama/GPU work. No automatic retries or duplicate server-side requests.

On context overflow: fail explicitly; never silently truncate retrieved evidence. On invalid quote, source, JSON, non-Korean summary or exhausted output: fail the approval gate. Reviewer must investigate original source; no runtime operation is executed by approval.

Space floor: report if root available space falls below 3GiB. No cleanup beyond the three already-approved pip/npm cache paths. The project needs only small source/SQLite/artifact files.

Evidence and audit records are local project files. Removing/reinitializing them requires a separate instruction; no script silently deletes them.

# Runbook

Use README commands from the isolated project. All new listeners must bind 127.0.0.1. No service, firewall, driver, VPN, Docker or existing model configuration change is required.

Before a live inference: inspect nvidia-smi compute applications and Ollama /api/ps; avoid overlap with unrelated jobs. Use only the existing qwen3:4b model and a single bounded request. Artifact traces contain synthetic evidence and no credentials.

On model timeout: app latches inference disabled, prevents another request and shows degraded evidence. Verify the owned request has ended using Ollama process/log observations before restarting ONLY this project process. Never stop unrelated Ollama/GPU work. No automatic retries or duplicate server-side requests.

On context overflow: fail explicitly; never silently truncate retrieved evidence. On invalid quote, source, JSON, non-Korean summary or exhausted output: fail the approval gate. Reviewer must investigate original source; no runtime operation is executed by approval.

## Shared inference lease

The default lease is `~/.cache/ax-lab/runtime/inference.lock` for the operating-system user running the app. Its location is independent of checkout depth. Projects 01 and 02 must use the same user and this same default, or the same explicit absolute `AX_LAB_INFERENCE_LOCK` value. This lease coordinates GPU occupancy only; corpus, sessions, permissions, analyses, reviews and audit state remain separate.

Optional explicit configuration, applied identically to both project processes:

```sh
export AX_LAB_INFERENCE_LOCK="$HOME/.cache/ax-lab/runtime/inference.lock"
```

The shell expands `$HOME` into an absolute path. Relative values, an unexpanded `~/...`, and an empty configured value are rejected. Changing configuration requires restarting the owned project process; no setting changes a running client's already selected path.

The client creates at most three missing parent directories, each with mode 0700. An existing final parent must already be owned by the current user and private; the client does not chmod existing directories. The lock is an owned regular file with mode 0600. Both parent and file opens reject a final symlink, and a directory descriptor anchors the file open. Permission or path failures stop the request before the network call and produce safe degradation. Nonblocking `fcntl.flock` and the in-process single-flight lock still reject overlap; the timeout latch remains unchanged. No lock contents carry evidence, identity or approval information.

Migration from the old checkout-relative `ax-lab/inference.lock` path: do not start clients on the new path while an old-path request is in flight. First verify the old owned lease and model request are idle, then restart only the owned app processes with the same new configuration. Do not remove either lock to bypass an active lease, stop unrelated workloads, or change global services. Lock files persist; a closed descriptor releases the OS lease.

Source for the 02 implementation: `workbench/llm.py::_configured_inference_lock` and `_open_inference_lease`, together with the existing acquisition/finally-close pattern in `request_json`. Copy this resource policy into 02's independent client when its inference path is implemented; importing 01's state or domain extractor is unnecessary. Before concurrent use, verify that both clients resolve the identical absolute path and test cross-process rejection. This patch does not claim that the future 02 integration has been validated.

Network-free checks:

```sh
python3 -m unittest discover -s tests -p test_llm.py -v
```

The tests use temporary private leases, including existing transport and timeout checks. They do not acquire the new shared runtime lease or perform a live migration.

Space floor: report if root available space falls below 3GiB. No cleanup beyond the three already-approved pip/npm cache paths. The project needs only small source/SQLite/artifact files.

Evidence and audit records are local project files. Removing/reinitializing them requires a separate instruction; no script silently deletes them.

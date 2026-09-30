# Project scope
Implement and test only in this independent remote project. Preserve all existing host services, models, datasets and authentication. No public bind, remote pushes, paid APIs or external data.
Use synthetic fixtures only. Every product claim must say this is an enterprise-workflow reproduction test, not real factory ROI/MTTR evidence.
Do not load a GPU model from a worker without the root's coordination; root owns all live inference. Worker API tests use deterministic mocks and clearly label mock artifacts.
One writer per assigned files. Root owns simulator/,workbench/llm.py,scripts/,docs except docs/ui.md,model/e2e evaluations and data/artifacts. Core worker owns core.py/server.py and core/HTTP tests. UI worker owns static/ and docs/ui.md.
Python standard library first; only add small official dependencies when materially necessary and coordinated. Keep free space above 3 GiB; report lower space immediately.
No model sees Docker socket, arbitrary shell, credentials, filesystem browsing, evaluation answers or approval write API.

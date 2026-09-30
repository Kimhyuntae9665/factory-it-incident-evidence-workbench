# Fixed synthetic retrieval comparison

Enterprise-workflow reproduction test. CPU ranking only; no generation or model accuracy measurement.

Shared ACL, latest revisions, queries, title/content index, case prior, top-k, and 4096-byte content budget.
Primary k=3. The k=4/6 rows are budget sensitivity checks, not combined headline scores.
Runtime default: token_overlap; hybrid comparison requires an explicit internal option.
L=normalized token intersection, P=0.2 for same-incident documents, C=exact code-token count, G=char3 cosine.
Token score=L+P; hybrid score=L+P+3*C+G. Ties use ascending document ID.
Query/gold span targets: suite.json (declared in fixed_suite); source: data/corpus.json.
Three failures with exact score components/ranks: failure-examples.json.
Observed fixed regression/tuning corpus; no new independent holdout has been evaluated.

| Category | Method | k | Queries | Doc recall | Span recall | All spans | MRR | CPU ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| counterevidence | char3_plus_code | 3 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.649 |
| counterevidence | char3_plus_code | 4 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.649 |
| counterevidence | char3_plus_code | 6 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.649 |
| counterevidence | token_overlap | 3 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.092 |
| counterevidence | token_overlap | 4 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.092 |
| counterevidence | token_overlap | 6 | 2 | 1.000 | 1.000 | 2 | 0.500 | 0.092 |
| digitless_error_code | char3_plus_code | 3 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.508 |
| digitless_error_code | char3_plus_code | 4 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.508 |
| digitless_error_code | char3_plus_code | 6 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.508 |
| digitless_error_code | token_overlap | 3 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.086 |
| digitless_error_code | token_overlap | 4 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.086 |
| digitless_error_code | token_overlap | 6 | 3 | 1.000 | 1.000 | 3 | 0.500 | 0.086 |
| exact_id | char3_plus_code | 3 | 3 | 0.333 | 0.333 | 1 | 0.333 | 0.617 |
| exact_id | char3_plus_code | 4 | 3 | 1.000 | 1.000 | 3 | 0.333 | 0.617 |
| exact_id | char3_plus_code | 6 | 3 | 1.000 | 1.000 | 3 | 0.333 | 0.617 |
| exact_id | token_overlap | 3 | 3 | 0.667 | 0.667 | 2 | 0.361 | 0.098 |
| exact_id | token_overlap | 4 | 3 | 1.000 | 1.000 | 3 | 0.361 | 0.098 |
| exact_id | token_overlap | 6 | 3 | 1.000 | 1.000 | 3 | 0.361 | 0.098 |
| korean_paraphrase | char3_plus_code | 3 | 4 | 0.333 | 0.400 | 0 | 0.500 | 0.557 |
| korean_paraphrase | char3_plus_code | 4 | 4 | 0.667 | 0.800 | 0 | 0.500 | 0.557 |
| korean_paraphrase | char3_plus_code | 6 | 4 | 1.000 | 1.000 | 4 | 0.500 | 0.557 |
| korean_paraphrase | token_overlap | 3 | 4 | 0.667 | 0.800 | 0 | 0.500 | 0.086 |
| korean_paraphrase | token_overlap | 4 | 4 | 1.000 | 1.000 | 4 | 0.500 | 0.086 |
| korean_paraphrase | token_overlap | 6 | 4 | 1.000 | 1.000 | 4 | 0.500 | 0.086 |
| latest_revision_positive | char3_plus_code | 3 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.565 |
| latest_revision_positive | char3_plus_code | 4 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.565 |
| latest_revision_positive | char3_plus_code | 6 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.565 |
| latest_revision_positive | token_overlap | 3 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.089 |
| latest_revision_positive | token_overlap | 4 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.089 |
| latest_revision_positive | token_overlap | 6 | 1 | 1.000 | 1.000 | 1 | 0.500 | 0.089 |
| log_config_health_coverage | char3_plus_code | 3 | 4 | 0.333 | 0.400 | 0 | 0.458 | 1.224 |
| log_config_health_coverage | char3_plus_code | 4 | 4 | 0.667 | 0.800 | 0 | 0.458 | 1.224 |
| log_config_health_coverage | char3_plus_code | 6 | 4 | 1.000 | 1.000 | 4 | 0.458 | 1.224 |
| log_config_health_coverage | token_overlap | 3 | 4 | 0.667 | 0.800 | 0 | 0.500 | 0.171 |
| log_config_health_coverage | token_overlap | 4 | 4 | 0.667 | 0.800 | 0 | 0.500 | 0.171 |
| log_config_health_coverage | token_overlap | 6 | 4 | 1.000 | 1.000 | 4 | 0.500 | 0.171 |

ACL/revision negatives: 16/16 passed, reported separately.

Exact-ID queries target document IDs absent from the indexed fields. Missing results are retained.
At k=6 most candidate pools are fully included, so high coverage is a budget result rather than strong ranking evidence.
Current code boost can prioritize code-bearing tickets/runbooks over configuration/health at tight budgets.
Small fixed previously observed corpus; no independent generalization, diagnosis, factory ROI, or model-quality claim.

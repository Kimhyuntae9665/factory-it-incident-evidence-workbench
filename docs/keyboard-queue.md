# Incident queue keyboard selection

This is a synthetic enterprise-workflow reproduction check. It does not establish real factory ROI or MTTR. It is separate from the source-candidate return check.

Native Tab and Enter selected incident INC-A-002 correctly at both desktop1440px and mobile390px before the change. Both incident-list renders removed the focused queue button, leaving focus on BODY. The source document and demo profile remained correct.

The selection now captures whether the active queue row initiated the request. After the current selection finishes, it restores the selected row on desktop. On mobile, the source task hides the queue, so it focuses the visible incident title. Initial login does not trigger this restoration. A later explicit focus choice during loading remains untouched. Existing request-version guards still exclude superseded selections; source authorization, citations and review rules are unchanged.

The browser driver uses its own tab in an existing sandboxed Chrome, native keyboard events and real synthetic-session/source reads. The delayed case pauses a real source GET before transmission, then verifies that selecting the review task during loading retains that task and focus. It does not fabricate source responses or call a model.

| Evidence | Result |
| --- | --- |
| Historical before run | 2 layout cases, 12 assertions, 2 native PNGs |
| Current after run | 2 layout cases, 19 assertions, 2 native PNGs |
| Existing source-candidate after regression | 2 layout cases, 17 assertions |
| Engineering tests | 50 passed |
| JavaScript syntax | Passed |
| Model requests in these checks | 0 |

Before mode requires the previous UI and is retained for historical reproduction. It cannot generate the old defect on the corrected UI. Current validation command: `python3 -m scripts.keyboard_queue_browser --phase after`.

The after assertions verify the exact selected row, visible mobile heading, continued Tab movement, return through mobile task controls, unchanged demo profile, current accessible source, native390px width/scale1 without horizontal overflow, and the delayed explicit focus choice. These assertions are distinct from engineering tests and the earlier UI refresh groups. Screen-reader testing is not included.

| Desktop | Mobile |
| --- | --- |
| [Before](demo/queue-keyboard/before/desktop-queue-selection.png) | [Before](demo/queue-keyboard/before/mobile-queue-selection.png) |
| [After](demo/queue-keyboard/after/desktop-queue-selection.png) | [After](demo/queue-keyboard/after/mobile-queue-selection.png) |

Token-free result metadata: [before](demo/queue-keyboard/before/checks.json), [after](demo/queue-keyboard/after/checks.json). The PNGs are actual browser captures with a short paint settle; the driver records their SHA-256 hashes.

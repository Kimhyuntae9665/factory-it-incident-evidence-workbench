# TRACE user interface

The interface is a Korean incident evidence workbench, implemented with local HTML, CSS, and plain JavaScript. It is explicitly labelled a synthetic enterprise-workflow reproduction test; it makes no real factory ROI or MTTR claim.

## Workflow

1. Choose an allowlisted demo profile from `GET /api/profiles` and start a session using `POST /api/session`.
2. Select an incident within that principal's site. Incident timeline, latest accessible evidence, and audit events load independently.
3. Search evidence by keyword. Open documents to read original text, revision, site and permitted role badges.
4. Choose the rule baseline or explicitly request the real local model. No model request is made on login, incident selection, search, or citation inspection.
5. Read separately labelled facts, hypothetical explanations, counterevidence, unknowns and citations. Source IDs open the document endpoint; quoted citations additionally call the exact-substring citation validation endpoint and highlight the quote using a DOM `mark` node.
6. Reviewer profiles can approve passing results or reject results. Degraded/error results and unknown/failed gates disable approval. Non-reviewer profiles see the permission explanation and disabled review controls. Existing decisions remain visible and cannot be duplicated through the UI.
7. Audit events link back to stored analyses. This also permits reviewing an analysis after reconnecting as a reviewer.

## API and safety

- Asset URLs are `/styles.css` and `/app.js`, matching the server's exact static whitelist.
- Authentication uses opaque tokens returned by the session endpoint, sent only as Authorization Bearer. Profile IDs are server allowlisted; the UI does not treat site/role badges as identity headers.
- Token/principal are stored only in memory and browser sessionStorage. A blocked sessionStorage leaves a usable memory-only session. No token appears in page text or URLs.
- All evidence, model responses, citations and audit text use textContent, createTextNode and DOM creation. No HTML parsing or untrusted interpolation is used.
- Only the contract JSON endpoints are called. No external resources, CDNs, uploads, model tools or additional network endpoints are introduced.
- The backend remains authoritative for site/role ACL, latest revision selection, citation validity and review gates. Disabled buttons are supplementary UX, not authorization.
- All mutations are single-flight with no automatic retries. Profile/incident switching and repeated execution are disabled during an active mutation. A timed-out analysis explicitly warns that server processing may continue; audit inspection is read-only and can recover stored analyses. Review timeouts reload the analysis to reconcile its recorded decision, without repeating the review request.
- GETs have a 15-second client deadline; explicit analysis requests have a 180-second deadline. Changing incident/profile cancels obsolete GETs and version checks prevent stale rendering.
- 401 clears the saved session and enables reconnecting. 403/404 and network/timeouts display Korean messages without revealing inaccessible content. Partially failed incident loads retain only successfully fetched sections. Empty evidence and timeline states are explicit.
- UTC is displayed explicitly for all rendered timestamps.

## Presentation and accessibility

A dark incident navigation rail anchors a light two-column source/analysis workspace, with restrained green, amber and red status treatments. The baseline and real-model modes have distinct labels, explanatory copy and selected colors; returned Ollama, mock, baseline and degraded modes remain explicit. At narrower widths the workspace stacks, and on mobile the incident list becomes horizontal.

Native buttons, labelled forms, radio fieldsets, keyboard focus, a skip link, polite status notices and reduced-motion support are included. Fonts use local fallbacks and do not trigger a font download.

## Validation

The implementation worker checks JavaScript syntax with the installed Node executable and statically checks referenced HTML IDs, contract paths and absence of innerHTML/eval/external dependencies. An in-memory Node mock-DOM smoke check covers login, single-flight analysis, literal untrusted text, quote verification/highlight, IT/reviewer permissions, audit recovery, recorded review, failed/degraded gate blocking and 401 reconnect/token cleanup. It invokes no HTTP server or model. Browser integration and live GPU checks are performed by the root agent; the UI worker does not launch services or request inference.


## Evidence-first UI refresh

The current layout uses a compact global demo-role switcher and a left incident queue. Case details lead into an expandable recorded-event timeline, a source-first workspace and structured review results. The document selector/search is collapsed initially so the selected original text remains visible in the desktop viewport. Existing source ACL, latest-revision selection, gate restrictions, baseline/model distinction and neutral operator review labels remain server-controlled.

Korean prose and controls use 16px where practical; dense facts, source text and metadata use at least 14px. Muted text colors are darker. Native focus outlines, source claim return, and three mobile task tabs support keyboard movement. Citation/document navigation and stored analysis restore explicitly choose auto scrolling under prefers-reduced-motion, then focus the destination; the return control restores the original claim when it remains connected.

The backend reports invalid opaque sessions as 403. The frontend verifies a protected-request 403 with a single-flight GET /api/incidents, readable by every valid demo profile. Only an invalid-session probe (401/403) clears the exact captured token and cached workspace. A successful probe preserves the token for a real authorization denial; failed/uncertain validation also preserves it. There is no automatic demo login or mutation retry. A session generation change cannot clear a newer token. Review-response timeout uses stored-analysis/audit GET reconciliation and records no second POST.

## Refresh evidence and limitations

scripts/ui_refresh_browser.py uses a dedicated sandboxed Chrome on loopback port 19086 and synthetic demo profiles. All its analyses are baseline-only: model requests are zero. It captures desktop/mobile before and after, timeline, expired-session recovery, equivalent 200% reflow and a stored reviewer record. The expired-token test performs only profiles/health and two incidents GETs before explicit user relogin. A protected-read ACL 403 and uncertain validation read are browser-response mocks; the valid session probe still reaches the real backend. Approved and rejected operator-redacted review cases exercise the actual backend and both remain neutral. The review-response delay is a labelled transport mock over one genuine synthetic review write, followed only by GET reconciliation.

Computed-style contrast sampling covers rendered text nodes against composited ancestor backgrounds, excluding inactive/opacity-reduced controls, opaque media and forced-color mode. The recorded result includes sample count, minimum contrast and any Korean text below 14px. This is a focused text check, not a complete WCAG conformance audit. The 200% case uses a 720×540 CSS viewport at device scale factor 2 to reproduce the reflow of a 1440×1080 display at 200%; it does not claim a manual browser-toolbar zoom test. Mobile checks use 390×1000, keyboard tab arrows/Home, task visibility and document-wide overflow. Screen-reader and high-contrast-mode audits remain future work. The old gallery/video show the previous layout; the ui-refresh demo captures show the current layout.


Final refresh result: 14 focused browser check groups passed; source scene 300 text nodes and reviewed scene 310, both minimum 5.222:1 with no Korean text below 14px. Existing engineering tests passed 50/50 in 12.295 seconds. Current PNGs and token-free result JSON are mirrored to docs/demo/ui-refresh/. Retrieval-failure rendering uses backend failure_stage metadata; its regression is explicitly a browser-response mock over baseline and cannot imply a real model failure. Public demo frames contain no model requests.

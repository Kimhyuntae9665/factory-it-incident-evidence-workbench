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

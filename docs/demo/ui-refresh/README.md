# Actual UI refresh evidence

All PNGs are unedited native Chrome viewport captures of synthetic demo data. The refresh workflow makes zero model requests. The old gallery and video are retained as prior-layout evidence; these files represent the current UI.

| Capture | Purpose |
| --- | --- |
| [before-desktop.png](before-desktop.png) | Desktop before the refresh |
| [before-mobile.png](before-mobile.png) | Mobile before the refresh |
| [after-desktop.png](after-desktop.png) | Current compact header, case queue and original quotation |
| [after-timeline.png](after-timeline.png) | Recorded event timeline expanded |
| [after-mobile-source.png](after-mobile-source.png) | 390px source task |
| [after-mobile-review.png](after-mobile-review.png) | 390px analysis/review task |
| [after-mobile-cases.png](after-mobile-cases.png) | 390px case queue |
| [after-expired-session.png](after-expired-session.png) | Real 403 invalid-token response, safe GET validation and explicit reconnect |
| [after-operator-neutral-review.png](after-operator-neutral-review.png) | Genuine operator-redacted reviewed result: neutral label and no private decision/comment |
| [after-reviewed-record.png](after-reviewed-record.png) | Genuine synthetic approved record after a mocked transport response delay |
| [after-200-percent-reflow.png](after-200-percent-reflow.png) | 720×540 CSS / DPR2 reflow equivalent of a 1440×1080 display at 200% |

[Browser result](result.json) contains 14 focused UI check groups; [operator decision regression](operator-neutral.json) exercises both approved and rejected real synthetic reviews and verifies neutral operator detail/audit presentation. The project engineering suite remains 50/50 passing and is a separate denominator.

The expiry check sends only four GETs: public profiles, public health and two incidents reads, then requires explicit demo reconnection. It does not restart a service. ACL 403 and uncertain probe cases are labelled browser-response mocks, with a real valid-session read in the ACL case. The review-response delay wraps one actual baseline review POST and reconciles via GET without a duplicate write. Retrieval failure metadata is separately mocked over baseline to verify copy and approval blocking; screenshots do not stage model success or model failure.

The primary source-review scene samples 300 rendered text nodes and the reviewed scene samples 310; minimum measured normal-text contrast is 5.222:1 with no Korean text below 14px. The sampler composites ancestor backgrounds and excludes inactive/opacity-reduced controls, media and forced colors. This is not a complete WCAG audit. Screen-reader/high-contrast-mode testing and manual browser-toolbar 200% zoom remain open. Source controls and dense metadata are not reduced to fit a viewport.

Reproduce with an existing sandboxed Chrome listener on loopback 19086 and the project app on 19080:

```bash
python3 -m scripts.ui_refresh_browser
python3 -m unittest discover -s tests -v
```

The optional --before flag is only for recording the currently served layout as a baseline before an edit; it does not reconstruct an earlier UI. The test helper uses only synthetic demo identities and baseline analysis. No browser install, external CDN or GPU inference is needed.

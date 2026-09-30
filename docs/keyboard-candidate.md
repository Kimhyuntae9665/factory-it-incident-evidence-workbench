# Candidate keyboard return evidence

Actual native Tab/Enter input reproduced a source-selection focus issue before the application was edited. Opening a candidate correctly focuses the document title. Returning to its source item previously focused the list summary because the original candidate node had been replaced. The update resolves the server document ID within the current authorized list and restores that exact selected candidate. The next Tab continues from the restored list position.

| Actual viewport | Before return | After return |
|---|---|---|
| Desktop1440×1080 | [List-summary focus](demo/candidate-keyboard/before/desktop-candidate-return.png) | [Selected-candidate focus](demo/candidate-keyboard/after/desktop-candidate-return.png) |
| Native mobile390×1000 | [List-summary focus](demo/candidate-keyboard/before/mobile-candidate-return.png) | [Selected-candidate focus](demo/candidate-keyboard/after/mobile-candidate-return.png) |

The browser report records actual focus identity and whether the former node remains connected. Screenshots come directly from sandboxed Chrome after paint settling, with native viewport scale1. No model output, screenshot compositing or replacement browser UI was used. Before captures were taken against the preceding source; current code does not recreate the old screen.

Validation sets remain separate:

- Before reproduction:2 layout cases,13 assertions,2 native screenshots,0 model calls.
- After verification:2 layout cases,17 assertions,2 native screenshots,0 model calls.
- Existing engineering suite:50/50 tests passed; JavaScript syntax passed.

After checks include native candidate selection/return, continued Tab movement, native mobile width/scale, and the existing server-verified citation quote/highlight and connected-claim return. Source/latest-revision/ACL/review behavior is unchanged. If the original document is absent from the current authorized list, the existing summary fallback remains available.

```sh
python3 -m scripts.keyboard_candidate_browser --phase after
python3 -m unittest discover -s tests
node --check static/app.js
```

[Before assertion record](demo/candidate-keyboard/before/checks.json) and [after assertion record](demo/candidate-keyboard/after/checks.json) include screenshot hashes and focus observations. These synthetic UI checks are not industrial model-accuracy, ROI or MTTR evidence.

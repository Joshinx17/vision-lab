# Development and tests

```powershell
npm test
npm run lint
npm run build
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_*.py
```

Native tests skip explicitly when their dependencies are unavailable. Do not
interpret a skipped test as a pass. They create synthetic HDF5 models in
.cache to test loading and class mapping; these are never real trained models.
The core test suite injects fake acquisition/processors to reproduce races
without a camera. Browser testing is needed in addition to those tests.

Use `npm start` to serve the built application. Rebuild and reload after source
changes. The source Vite dev command is not the supported all-module runtime:
the Python server supplies the API and copied MediaPipe assets.

## Add a module

Implement the lifecycle in frontend/src/modules. Add a factory and display
metadata to registry.js, module-specific controls/results if needed, and tests.
Never acquire a camera in a module. Return serializable results; clear internal
native resources/event listeners in dispose. Throw errors for unavailable
dependencies instead of returning invented predictions.

## Baseline and Git

`docs/source-baseline.json` records hashes/commit IDs of original tracked files.
Nested .git directories were not removed. No automatic commit or destructive
restructure was performed; the original histories and source trees remain
available locally. The root .gitignore excludes original folders to avoid
accidentally committing nested repositories as broken gitlinks.

The new frontend/backend/docs/tests can be committed normally. Copying the
root repository will not include the ignored original repositories unless you
explicitly preserve them separately. Review attribution/model licensing before
public distribution; source READMEs claim licenses but do not all supply license
files. A source hash manifest records provenance, not redistribution permission.

Suggested incremental commits: docs source audit, feat unified core/modules,
test lifecycle and native preprocessing, docs setup and verification. Review
the working diff first; this integration creates no branch outside this folder.

## Manual runtime acceptance

1. Start on a machine with a webcam; allow camera permission on localhost.
2. Vision-XE: verify face box, landmarks, expressions and changing analytics.
3. Enable exam demonstration; test absence, multiple faces, cooldown, restart.
4. Switch to Air Write; test one-finger draw, two-finger erase, pinch, no-hand,
   color/brush/clear/grid; compare finger/overlay alignment at each resolution.
5. Switch to Sign with a real compatible model; verify crop, letter/confidence,
   full-frame fallback, upload image and below-threshold presentation.
6. Repeat Vision -> Air -> Sign -> Vision, and Stop/Start several times;
   confirm camera indicator extinguishes on stop and tab close.
7. Capture samples; verify saved pixels contain no annotation. Train only with
   a suitable dataset/new model filename and record held-out metrics.

The camera probe script only opens device0 and reads ten frames without saving
them. It does not establish successful behavior of the browser modules.

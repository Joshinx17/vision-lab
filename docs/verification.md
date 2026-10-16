# Verification record

Latest work verified on 2026-10-17. Synthetic tests, browser observations and
unavailable hardware/model acceptance are distinguished below.

| Check | Expected | Actual | Status |
|---|---|---|---|
| npm test | Lifecycle/assets/source invariants pass | 13 passed, 0 failed | PASS |
| Python native/API/resource tests | Config, payloads, catalog, switching, ownership, preprocessing and model loading | 27 passed, 0 skipped, Python3.13 | PASS |
| Synthetic replacement | Different size/color/labels work through adapter | 96x80 RGB two-class .keras produced expected synthetic label | PASS, synthetic only |
| Original CNN training | One epoch runs and saves | Four synthetic zero images; temporary fixture removed | PASS, not accuracy |
| npm run lint | No ESLint errors | Exit0 | PASS |
| npm run build | Website and local assets build | Exit0; face-api chunk/fs warnings remain | PASS with warnings |
| Resource API | Empty candidate selectable without breaking service | Endpoint and profile tests pass | PASS |
| Browser missing-model feedback | Actionable message before camera opens | Candidate path/instructions displayed | PASS, observed |
| Browser model selection | Original/candidate configuration switches | Selection/path diagnostic change in website | PASS, observed |
| Source preservation | Original files unchanged | Baseline SHA256 tests pass | PASS |
| Browser pointer drawing | Stroke/clear without webcam | Observed in prior 2026-10-07 session | Prior observation |
| Face model loading | Provided weights load | Current website reached Waiting for camera after model initialization | PASS, observed initialization |
| Native webcam acquisition | Device opens/reads/releases | Camera0 read ten 640x480 frames on 2026-10-17, no images saved | PASS |
| Browser webcam/modules | Live overlays/gestures/switching work | Embedded-browser permission timed out; UI recovered with clear message | NOT VERIFIED |
| Real sign predictions/accuracy | Evaluated model works | No trained model/dataset supplied | NOT VERIFIED |
| Legacy Python hand tracking | mp.solutions hand crops | Installed MediaPipe0.10.32 lacks mp.solutions | NOT VERIFIED |
| Clean Python setup | Pinned3.11/3.12 stack installs/passes | Neither interpreter installed; tested existing3.13 | NOT VERIFIED |
| Public deployment | HTTPS domain/backend/multi-user behavior | Not deployed; loopback service only | NOT IMPLEMENTED |

Native versions actually tested: OpenCV4.12.0, TensorFlow2.20.0-rc0,
MediaPipe0.10.32, NumPy2.2.6 under Python3.13. These are not the clean
requirements.txt pins. Synthetic tests disable/use no legacy hand tracking;
crop geometry uses controlled landmark fixtures. No synthetic model is
shipped as recognition weights.

Tests required loopback/subprocess/filesystem permission in this Windows
sandbox. Permission failures were rerun with permission. The intentionally
corrupt model test logs an expected HDF5 exception. Keras/HDF5 deprecation
warnings remain.

No real-world FPS, recognition accuracy, memory, CPU or sensor-to-display
latency result is claimed. Follow docs/development.md manual acceptance with
a webcam, usable legacy tracking stack and an evaluated sign model.

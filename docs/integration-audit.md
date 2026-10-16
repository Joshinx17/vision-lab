# Source audit and integration decision

Audit date: 2026-10-07. No source project is deleted or moved. Each original
folder contains its own Git history; the parent initially tracks only README.md.
`source-baseline.json` records tracked source hashes and original commit IDs.

## Vision-XE

- Purpose: face detection, 68 facial landmarks, seven expression scores,
  rolling analytics, and a demonstration examination monitor.
- Technology: JavaScript, React 19, Vite 8, face-api.js 0.22.2; Express 5/ws 8
  relay. npm lockfiles are present. No working tests.
- Entry points: frontend/src/main.jsx -> App -> WebcamFeed, LiveDashboard,
  ExamPage; server.js listens on fixed port 5000. socketConnection.js is unused.
- Input/output: getUserMedia 640x480 -> TinyFaceDetector -> landmarks ->
  expressions -> canvas and JSON WebSocket broadcast. Live processing every
  200ms; examination every 300ms. These are intervals, not measured FPS.
- Reusable: bundled face model manifests/shards, detection chain, expression
  bars/history, examination rules (3-second absence, 5-second cooldown,
  normalized nose displacement >0.35, expression >0.4, three warnings).
- Problems: WebcamFeed never releases camera; async intervals can overlap;
  dashboard reconnects after unmount and loses its producer on route change;
  permissive relay broadcasts unvalidated data; hardcoded URL; model errors
  leave exam waiting; audio contexts and timers leak; splash reports fictitious
  loading progress. Expression scores do not establish cheating or intent.
- Baseline: frontend production build PASS (Node 25.2.1; compiler needed
  subprocess permission). Face model shards exist. Real camera NOT VERIFIED.
- Integration: keep React/face-api algorithms and weights, move processing
  into a lifecycle adapter, keep analytics alongside active camera, retain
  exam rules as an explicitly labelled demonstration. No object tracking or
  pose estimator exists in this source.

## Air Write

- Purpose: fingertip drawing, seven neon colors, brush size, eraser, clear,
  grid, keyboard shortcuts, mouse/touch fallback.
- Technology/entry: single index.html, plain JS/CSS, unpinned MediaPipe Hands
  scripts from jsDelivr. camera_utils and control_utils are unused.
- Pipeline: browser webcam -> Hands (two hands, first used, complexity 1,
  detection .7/tracking .6) -> index-tip coordinates -> .45 smoothing ->
  index extension .03, pinch distance .06, two-finger eraser -> four-pass
  glow strokes and destination-out circular erase.
- Problems: no shutdown/cancellation; duplicate resize handlers; frame errors
  escape async loop; no-hand leaves eraser cursor stale; cover-scaled video
  mismatches coordinates; erase-to-draw can bridge strokes; CDN failures
  silently replace tracking with pointer mode. No tests or configuration.
- Baseline: source inspected; browser/camera/CDN operation NOT VERIFIED.
- Integration: extract gesture/stroke logic and preserve thresholds/rendering,
  use core camera and loop, align canvas with video aspect ratio, expose
  pointer mode explicitly, pin and serve MediaPipe assets locally.

## Sign Language

- Purpose: static A-Z image CNN, live OpenCV inference, Streamlit snapshot/
  upload inference, raw dataset capture, training controls/history/reference.
- Technology: Python; TensorFlow/Keras, OpenCV, MediaPipe Solutions, NumPy,
  sklearn, matplotlib, Streamlit. pandas imported but unused. Unbounded lower
  dependency constraints; no lockfile or tests. No environment variables.
- Entry points: app.py, run_recognition.py, create_dataset.py, train_model.py.
  Core: SignLanguageDetector, preprocess_image, detect_and_crop_hand,
  prepare_dataset. Cameras opened independently in CLI scripts; Streamlit
  uses browser snapshots. Paths depend on current working directory.
- Model: expected sign_language_model.h5, NOT PROVIDED. Dataset directory
  exists but contains no images. asl_reference.png exists and is ignored.
- Exact input: BGR frame; RGB conversion only for MediaPipe; bbox extrema
  with 20px padding clamped to image; BGR crop (full-frame fallback if no
  hand), OpenCV resize 64x64, float32 /255, batch (1,64,64,3).
- Architecture: Conv2D 32/64/128 (3x3, ReLU), each MaxPool2D 2x2,
  Flatten, Dense128 ReLU, Dropout .5, Dense26 softmax. Class index 0=A..25=Z.
  Original confidence is softmax maximum *100, not calibrated accuracy.
  Static images cannot model J/Z motion sequences.
- Training: one-hot labels; stratified 80/20 split seed42; Adam/categorical
  crossentropy; rotation/zoom/contrast .1; early stopping patience5.
- Problems: dubious `import mediapipe.solutions` disables tracking; full-frame
  fallback can confidently classify backgrounds; 52 total samples cannot
  support a 26-class stratified 20% test split; capture filenames overwrite
  on CLI restart; missing-hand dereference in UI; invalid matplotlib rgba
  strings; no native resource cleanup; globally cached mutable detector.
- Baseline: run_recognition.py FAILS with missing cv2 under Python 3.14.6.
  Only Python 3.13/3.14 installed; no TensorFlow/MediaPipe/OpenCV/Streamlit.
  Real inference, training, accuracy, latency: NOT VERIFIED.
- Integration: reuse Python CNN/preprocessing/training source; a loopback
  frame service avoids changing model format or training distribution.
  Retain full-frame fallback but mark it. Missing models must not produce
  fabricated predictions. Capture/training/upload become unified UI tools.

## Shared components and conflicts

| Component | Consumers | Decision |
|---|---|---|
| Browser camera | all live modules | one owner; release on stop/switch/failure |
| Frame scheduling | all | serialized processing; await in-flight work before dispose |
| Results/metrics | all | module, timestamp, processing_ms plus meaningful payload |
| Canvas dimensions | all | actual video dimensions, one mirrored coordinate space |
| Hand landmarks | Air/Sign | retain JS and Python implementations: model preprocessing fidelity outweighs forcing reuse across runtimes |
| Model loading | face/sign | lazy, validate, explicit failure; no retraining automatically |
| Configuration/logging | all | root config/env, loopback service and bounded results |

React is reused; no new frontend framework. Python stays for the actual CNN.
The Express relay is superseded by in-process results plus same-origin API;
original relay remains available in the preserved source. The unified service
never opens a camera. No camera index exists in browser APIs: use deviceId.
Ports are configurable and bind to loopback. No external accounts or hosting.
Use Python 3.11/3.12 for the pinned legacy MediaPipe Solutions stack; do not
mix the original unbounded requirements into the new environment.

## Planned architecture (before implementation)

React shell -> registry -> Core Camera + serial Pipeline -> selected adapter
-> structured result + module rendering. Vision-XE stays browser face-api;
Air Write stays browser MediaPipe; Sign sends bounded frames to local Python
and keeps exact crop/normalization/CNN. A single root command launches the
service and built frontend. Original projects are provenance, not launch targets.
Testing covers cancellation/races, geometry/gestures, rules, config, input
validation, preprocessing, model failures and API; camera/real-model checks
must be reported separately. No performance optimization without measurement.

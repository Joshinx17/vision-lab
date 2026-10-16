# Architecture

Vision-Lab is a local modular application. React/Vite and face-api.js are
reused from Vision-XE, gesture/stroke code is extracted from Air Write, and
the Python CNN/preprocessing/training code is adapted from Sign Language.
It is not a launcher for three separate applications.

```text
React shell + module registry
         |
Camera owner (getUserMedia, mirrored raw pixels)
         |
Serialized frame pipeline + timing + generation guard
         |
         +-- Vision-XE: face-api.js -> detection/landmarks/expressions
         +-- Air Write: MediaPipe JS -> gesture -> stroke/canvas
         +-- Sign: JPEG -> loopback Python -> BGR crop -> Keras CNN
         |
Structured result + canvas overlay + live analytics
```

## Ownership and lifecycle

`Camera` owns the MediaStream. `Pipeline` owns the selected module, the
requestAnimationFrame callback, frame canvas, and overlay. Modules implement
`initialize({config, canvas})`, `process(frame)`, optional `render(result,
canvas)`, and `dispose()`. Registry entries contain display metadata/factories.
There is no module-name conditional in the core processing path. UI sections
remain module-specific because the controls and results actually differ.

Start: dispose prior module, initialize selected module, acquire camera,
schedule frames. Capture uses actual video dimensions. Every frame is mirrored
once into a raw canvas. The video display is mirrored via CSS; overlays are
not mirrored. Both share the same aspect ratio, preventing cover-crop drift.
The raw frame, never the annotation canvas, is sent to the classifier or saved.

The next callback is queued only after processing completes. A generation
guard discards results from stopped sessions. Stop invalidates the generation,
cancels the next frame, releases camera tracks immediately, awaits in-flight
work, disposes the module, and clears overlays. Camera requests that resolve
after cancellation release their streams. A 15-second camera acquisition
timeout prevents indefinite permission waits. Page hiding/unloading releases
the camera. Native/WASM initialization may take time; do not refresh repeatedly.

## Runtime boundary

One Python standard-library HTTP server serves `frontend/dist` and `/api`.
It binds only 127.0.0.1. No Express relay, WebSocket or Streamlit process is
needed. Python dependencies load lazily, so the UI and browser modules work
without TensorFlow. The root Node launcher chooses a repository-local venv
when present, forwards termination, and points library caches inside the repo.

Python receives compressed mirrored BGR-compatible images, detects/crops hands
using the original Python MediaPipe pipeline, and performs unchanged 64x64
normalization and CNN inference. JS and Python MediaPipe implementations stay
separate deliberately: sharing landmarks across languages would alter the
original sign preprocessing without an available trained-model baseline.

The sign detector has a lock because native hand tracking is stateful. Training
runs in one background thread; inference is rejected while training is running.
The status endpoint remains responsive. Dataset capture does not use the
detector. Training refuses to overwrite any existing model; a complete model is
renamed from a temporary file only after training finishes. History is saved
as `data/training_history.json`.

## Results and measurements

Common fields: `module`, `timestamp` (Unix milliseconds), `processing_ms`,
`fps` (processed frames, including scheduling delay). Payloads are documented
in modules.md. `inference_ms` covers Python preprocessing plus classification.
Browser processing time includes transport for Sign. These are not
sensor-to-screen latency or CPU/memory measurements. No hardware throughput
claim is made; no speculative performance optimization was introduced.

## Input and file boundaries

API accepts local Host/Origin only, requires a custom header on POST, never
enables CORS, limits JSON to 4.1 MB, images to 3 MB/2.1 megapixels, validates
formats before OpenCV decoding, and checks training options/classes. Static
paths and configured model/data paths must resolve inside this repository.
Frames are retained only when the user explicitly captures dataset samples.
Only trusted local model files should be used; model upload is not an API.

This is a single-user local tool, not an internet-facing service. No cloud,
accounts, database, production web server, or authentication system is added.

## Resource catalog and adapter boundary

config/resources.json now defines sign-model profiles, labels/preprocessing,
face model URLs, MediaPipe asset base/options and the optional chart. Resources
are checked without importing native ML packages. Missing/invalid resources
are returned to the website; absent trained weights are kept absent.
backend/model_adapters.py provides explicit trusted factories. The implemented
keras_image adapter accepts configured image dimensions, BGR/RGB, affine
normalization, labels and crop/no-hand behavior. Only original-contract profiles
can use the existing trainer. Other runtimes need registered adapter code.

The website exposes diagnostics, selection and apply/reload actions. Profile
switching validates configuration before closing old resources. Sign inference
uses browser session ownership: other tabs cannot unload or replace its model,
and an abandoned lease can be reclaimed after 60 seconds without predictions.
Simultaneous stop/restart awaits a shared asynchronous teardown before opening
the next module. Profile selection is process-local; startup choice is stored
in the editable catalog. Public hosting remains outside the current runtime.

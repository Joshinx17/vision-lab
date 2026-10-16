# Setup and local distribution

From the Vision-Lab root, use Node 22.12+ and Python 3.11 or 3.12 for the full
native stack. No GPU/CUDA is required. A browser with getUserMedia/WebGL and a
working OS camera driver is required for live input. Browser camera selection
uses device IDs; it does not use an OpenCV camera index.

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.txt
npm --prefix frontend ci --cache .cache/npm
npm run build
Copy-Item .env.example .env
npm start
```

Open http://localhost:8765 in Chrome/Edge. Press Ctrl+C in the terminal to
stop. If Python 3.12 is not installed, setup cannot proceed with that command;
install a compatible interpreter yourself, or use 3.11 in the same command.
No installer modifies system Python or installs dependencies globally.

Linux/macOS:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --cache-dir .cache/pip -r requirements.txt
npm --prefix frontend ci --cache .cache/npm
npm run build
cp .env.example .env
npm start
```

The UI, Vision-XE and Air Write also run with ordinary Python 3.10+ and no
native Python packages; install frontend dependencies/build, then `npm start`.
Sign inference/training/capture require the native requirements. This is an
explicit partial-runtime option, not verification of all three modules.

## Configuration

`.env`: VISION_PORT (1024–65535), VISION_MODEL (repository-relative .h5/.keras),
VISION_LOG_LEVEL (DEBUG/INFO/WARNING/ERROR), optional VISION_PYTHON (executable
inside repository). Default: .venv interpreter if present, otherwise `python`.
Settings are validated at startup. The service always binds to 127.0.0.1.

UI: camera device, resolution, target FPS, sign confidence. Changes apply on
next start. These settings are session-local. Model path changes need restart.
Runtime paths are rooted at the project, irrespective of shell directory.

## Models and data

The three face-api models are supplied in frontend/public/models. Air Write's
MediaPipe package includes its assets, copied during build. No sign model or
dataset was supplied. Provide a trusted compatible model at
models/sign_language_model.h5, or collect/train from the workbench. Do not
rename arbitrary models into that path. No retraining was performed as part of
integration. Dataset samples live in data/asl_dataset/A..Z and are Git-ignored.

## Distribution decision

Distribute this repository plus npm lockfile and Python requirements, or a
prebuilt frontend/dist with the Python backend and its environment. Node is
needed for build/launcher; a prebuilt distribution can run directly with
`python -B -m backend.server`. No source folder from the original three
projects is required by the unified runtime.

This service is designed for one local user. Docker and remote hosting were
not introduced: browser camera permission/HTTPS and local inference semantics
would need separate verification. No deployment has been claimed.

## Dependency strategy

Frontend lockfile controls transitive versions. MediaPipe Hands JS is pinned;
face-api is retained for weight/algorithm fidelity. node-fetch is overridden
to patched 2.7.0 instead of downgrading face-api in response to npm's suggested
major change. Compatible npm advisory fixes are applied.

Python pins target the legacy MediaPipe Solutions API (0.10.21), TensorFlow
2.18, NumPy1.26 and OpenCV contrib4.11. MediaPipe already needs contrib OpenCV:
do not also install opencv-python/headless, which share the cv2 namespace.
Python's complete transitive environment is not locked. Clean installation of
this pinned environment remains NOT VERIFIED on this machine (only 3.13/3.14
were available). See verification.md for actual installed versions tested.

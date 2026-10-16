# Vision-Lab

A local computer-vision workspace integrating Vision-XE, Air Write, and static
ASL alphabet classification behind one camera pipeline and interface.

**Status:** integration implemented; automated and browser checks are recorded
in [verification](docs/verification.md). Full live-camera acceptance and real
sign recognition are **NOT VERIFIED**: camera0 was unavailable and no trained
sign model or dataset was provided. Do not treat synthetic model tests as
recognition accuracy results.

## Run

From this folder in PowerShell (Node22.12+; Python3.11/3.12 for native CV):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --cache-dir .cache/pip -r requirements.txt
npm --prefix frontend ci --cache .cache/npm
npm run build
Copy-Item .env.example .env
npm start
```

Open [Vision-Lab](http://localhost:8765). Select a module and press **Start
camera**. **Stop**, module switching, and closing the tab release the webcam.
Python3.12 must already be installed for the first command. See
[setup](docs/setup.md) for Linux/macOS, configuration, and the browser-only
capabilities that run without native Python packages. The app does not install
anything globally.

To enable sign prediction, provide your trusted compatible model at
`models/sign_language_model.h5`. No such model was in the supplied project.
Dataset capture and training are explicit workbench actions, not automatic
fallbacks for missing weights. See [model requirements](models/README.md).

## Capabilities

| Module | Integrated behavior |
|---|---|
| Vision-XE | Face boxes, 68 landmarks, expression scores, live bars/history, original exam-rule demonstration and optional warning sound |
| Air Write | Hand tracking, index drawing, pinch pause, two-finger erasing, smoothing, neon colors/brush, clear/grid, keyboard and mouse/touch controls |
| Sign Language | Original BGR crop/CNN pipeline, live and image prediction, confidence/fallback feedback, raw capture, A–Z counts/reference, training parameters/history |

The examination rules are a demonstration; expression scores do not establish
cheating. Sign classification uses single images and does not translate
continuous signing or represent motion letters reliably.

## Architecture and stack

```text
React UI -> module registry -> shared camera + serialized frame pipeline
                             |-- face-api.js (Vision-XE)
                             |-- MediaPipe JS (Air Write)
                             `-- local Python frame API (Sign)
                                  OpenCV + MediaPipe + Keras CNN
                          <- structured result + overlay + measurements
```

The existing React/Vite stack is reused. Browser modules process locally.
Sign frames are sent only to the loopback Python service, which never opens
a webcam. A standard-library HTTP server serves the built UI/API. NumPy,
OpenCV, Pillow, MediaPipe, TensorFlow/Keras and scikit-learn support native sign
processing/training. No cloud, database, paid service, or separate app launch.

One frame is processed at a time. Stop/switch invalidates pending results,
releases camera tracks and disposes module resources. See
[architecture](docs/architecture.md) and [module details](docs/modules.md).

## Repository

```text
vision-lab/
├── frontend/
│   ├── src/core/            # Camera, pipeline, config, API
│   ├── src/modules/         # Lifecycle adapters and algorithms
│   ├── src/App.jsx          # Unified workspace and workbench
│   ├── public/models/       # Supplied face-api weights
│   └── package-lock.json
├── backend/
│   ├── server.py            # Loopback static/API service
│   ├── service.py           # Sign lifecycle, capture and training
│   ├── config.py
│   └── sign/                # Adapted original CNN/preprocessing
├── models/README.md         # Sign model contract and provenance
├── tests/                   # JS core/assets + Python API/native tests
├── scripts/                 # Single launcher and camera probe
├── docs/                    # Audit, baseline, architecture, verification
├── requirements.txt
├── package.json
├── .env.example
├── Vision-XE/               # Preserved original nested Git repo (ignored)
├── air-write/               # Preserved original nested Git repo (ignored)
└── sign-language-recognition/ # Preserved original nested Git repo (ignored)
```

Runtime-generated `.cache`, `logs`, `data`, `.venv`, model files and built
assets are ignored. The original source folders are preserved as local
provenance; the unified application does not import or launch them.
[The pre-integration audit](docs/integration-audit.md) explains what was reused,
adapted and superseded. No original source file or history was deleted.

## Tests

```powershell
npm test
npm run lint
npm run build
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_*.py
```

Native tests report skips if dependencies are unavailable. Synthetic fixtures
exercise loading/preprocessing/class mapping, not accuracy. The
[verification matrix](docs/verification.md) separates automated tests, browser
observations, hardware failures and work still needing a real model/webcam.
See [development](docs/development.md) for acceptance steps and new modules.

## Troubleshooting and roadmap

Use [troubleshooting](docs/troubleshooting.md) for permissions, missing models,
MediaPipe compatibility, build errors and training prerequisites. Backend
errors go to `logs/vision-lab.log`; browser errors also appear in the UI/console.

- **P0:** supply the original trained sign model, connect a webcam, complete
  real module/switching acceptance and clean pinned-environment installation.
- **P1:** collect representative evaluation data, verify confidence behavior,
  record reproducible native dependency lock and CPU/memory/latency baseline.
- **P2:** persistent model metadata/history loading, drawing export, additional
  camera tests and maintained-model-library migration with parity checks.
- **P3:** evaluate temporal sign recognition and packaging after local
  behavior is verified; no remote deployment is claimed.

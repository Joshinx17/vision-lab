# Vision-Lab

A local computer-vision workspace integrating Vision-XE, Air Write, and static
ASL alphabet classification behind one camera pipeline and interface.

**Status (2026-10-17):** the unified website, resource catalog and model-profile
workflow are implemented. Automated and browser checks are recorded in
[verification](docs/verification.md). Full live-camera acceptance and real
sign recognition are **NOT VERIFIED**: browser camera acceptance is still
outstanding and no trained sign model or dataset was provided. A fresh native
camera0 probe did read ten 640×480 frames successfully. Do not treat synthetic model tests as
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
`models/sign_language_model.h5`, or configure another profile in
`config/resources.json`. No such model was in the supplied project.
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
│   ├── resources.py         # Catalog validation and missing-file diagnostics
│   ├── model_adapters.py    # Explicit inference adapter factories
│   └── sign/                # Adapted original CNN/preprocessing
├── config/resources.json   # Editable model profiles and browser resource paths
├── models/
│   ├── README.md            # Model contract and provenance
│   └── sign-language/
│       ├── asl-labels.json  # A–Z labels in model-output order
│       └── candidate/       # Intentionally empty replacement-model slot
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

Verification on 2026-10-17: **13 JavaScript tests passed; 27 Python tests passed
with no skips under the existing Python3.13 environment; lint and production
build passed.** Build still reports the large face-api chunk and fs
externalization warnings. Native tests include a synthetic replacement model
with 96×80 RGB input/two labels and original CNN smoke training. Neither test
establishes real recognition accuracy. The documented clean Python3.11/3.12
installation and actual live-camera acceptance remain NOT VERIFIED.

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

## Website access and startup boundaries

The whole user workflow is available through the website: module selection,
live camera, expression analytics, exam demonstration, Air Write tools,
image prediction, dataset capture, training, model-profile selection and
resource diagnostics. There is one launcher, `npm start`, and one browser
address, `http://localhost:8765`. The launcher serves the built website and
Python API together. The original three applications are not started.

This currently runs as a **local website on the computer running Vision-Lab**.
It is not published to a public domain. The server deliberately listens on
127.0.0.1 and rejects foreign Host/Origin headers. Opening a static HTML host
alone will not provide the Python classifier/trainer. A publicly hosted version
would need an HTTPS deployment, a suitable backend server, access control for
training/dataset writes, resource limits and separate multi-user sessions.
Those deployment features are not implemented or verified.

The camera always belongs to the browser accessing the website. The Python
service receives frames; it never opens a second webcam. Only explicit dataset
capture saves frames to disk. Inference does not upload frames to a cloud API.

## Models and resources: everyday workflow

Use **Models & resources** in the website. It reports missing weights, labels,
face-model manifests/shards, browser hand-tracking assets, Python inference
dependencies and the optional reference image. A missing sign model does not
prevent Vision-XE or Air Write from running. A broken camera does not prevent
Air Write's explicit **Mouse / touch** mode.

Missing trained models are deliberately absent. There is no empty binary
pretending to be a model, no dummy recognizer and no automatic retraining.
The candidate directory contains only `.gitkeep`. Source reference/face files
that were provided are retained.

1. Place a trusted model under `models/`, preferably in its own version folder.
2. Put its labels in a JSON array, ordered exactly like the model outputs.
3. Add a profile to `config/resources.json`; describe the actual input contract.
4. Select it in **Sign model profile**. The website stops the current camera
   session, disposes the previous adapter, clears results/preview and applies
   the new contract. Selecting an empty model slot is allowed for setup.
5. Press **Start camera** or upload an image. Model loading validates tensor
   dimensions, class count and probability output. Errors appear in the UI.
6. If you change profile metadata or labels, click **Apply / reload selected
   profile**. If you only add missing weights at the already configured path,
   refresh resources and start again.

**Refresh resources** inspects the current files; it does not interrupt a
running camera or silently replace a loaded model. Applying a profile is the
explicit replacement action. UI selection lasts for the server process; set
`active_sign_profile` in the catalog to choose the next startup default.
`VISION_MODEL`, if explicitly set in .env, overrides the original-contract
startup path for compatibility. Prefer the catalog and leave that variable unset.

### Profile example and supported model contracts

The supplied candidate entry is a template. A different compatible image
classifier can use a profile such as:

```json
{
  "id": "asl-v2",
  "name": "My evaluated classifier v2",
  "adapter": "keras_image",
  "path": "models/sign-language/v2/model.keras",
  "labels_path": "models/sign-language/v2/labels.json",
  "input": {
    "width": 96,
    "height": 80,
    "color": "RGB",
    "scale": 0.00784313725490196,
    "offset": -1
  },
  "hand_crop": {
    "enabled": true,
    "padding": 20,
    "no_hand": "skip"
  }
}
```

This is an **example contract**, not an included model or accuracy claim.
Add the entry to `sign_profiles`; do not replace the whole catalog with it.

| Field | Meaning / accepted values |
|---|---|
| `id` | Unique lowercase identifier; letters, digits, hyphen/underscore, up to 64 characters |
| `adapter` | `keras_image` is implemented; other families need an adapter factory |
| `path` | Repository-contained trusted .h5 or .keras file |
| `labels_path` | Repository-contained JSON array; unique, nonempty labels in output order |
| `input.width/height` | Integers 16–1024; channels-last input is (N,height,width,3) |
| `input.color` | BGR or RGB; source decode is BGR |
| `input.scale/offset` | float32 preprocessing: pixel × scale + offset; original /255 behavior is preserved |
| `hand_crop.enabled` | Use Python MediaPipe hand ROI when available, or classify the whole input when false |
| `hand_crop.padding` | 0–256 pixels around detected bounds |
| `hand_crop.no_hand` | `full_frame` preserves original fallback; `skip` returns no label/zero confidence |

The implemented adapter supports one three-channel image tensor and one vector
of normalized class probabilities. It does not automatically infer preprocessing
from a model filename. Logits, grayscale, multiple input/output tensors,
segmentation, temporal sequences, ONNX, PyTorch and TensorFlow Lite inference
are not implemented by this adapter. A model with a newer training architecture
can work without application changes if it still meets the declared interface
and uses layers supported by installed Keras.

### Add a different model runtime

`backend/model_adapters.py` is the trusted registry. Add one factory and register
its key in `ADAPTERS`; config strings never become arbitrary imports or eval.
The factory receives the validated profile and must validate/load its model,
release partial resources on failure, and return an object with:

- `model`: non-None while loaded (used for status).
- `predict(bgr_frame)`: returns `letter`, confidence in 0–100,
  `bbox` (x,y,right,bottom or None), and `landmarks` (MediaPipe-compatible or None).
- `close()`: closes tracking/runtime resources and drops the loaded model.

The service normalizes confidence to 0–1 and adds `accepted`, `profile_id`,
`fallback` and `inference_ms`. Keep those public results stable so the UI,
camera pipeline and other modules need no changes. If a future model has
different inputs or result semantics, extend its adapter and its module
explicitly; arbitrary models are not interchangeable merely by renaming files.
The current common profile schema is for image classifiers and may need a
versioned extension for sequence/landmark models.

### Replace face or hand-tracking resources

Vision-XE reads `vision_xe.models` in the catalog. Put replacement face-api
compatible manifests/shards beneath `frontend/public/`, change those three URL
directories, run `npm run build`, and reload the website. Manifest filenames
remain `tiny_face_detector_model-weights_manifest.json`,
`face_landmark_68_model-weights_manifest.json`, and
`face_expression_model-weights_manifest.json`. An unrelated face detector needs
a new browser module adapter in `frontend/src/modules/`.

Air Write reads `air_write.asset_base` and `air_write.options`. The build copies
the pinned MediaPipe Hands package to `/mediapipe`. You may provide a complete
compatible resource bundle under `frontend/public/your-folder` and point
`asset_base` at `/your-folder`. Keep its JS/WASM/graph/TFLite files together.
Changing the runtime path requires a page reload to avoid mixing two global
Hands implementations. A newer Tasks API or a different landmark format
requires an adapter; replacing a lone TFLite file is not sufficient.

Set `reference_image` to a local public URL for an updated reference chart.
Absent reference images produce UI guidance. Public files are copied at build
time; Python sign models are read directly at runtime and need no Vite rebuild.

## Conflict prevention and lifecycle details

| Potential conflict | Implemented handling |
|---|---|
| Three modules opening the camera | Only core Camera calls getUserMedia; module processors receive frames |
| Inference calls overlapping | Serialized frame loop; next frame starts after prior inference completes |
| Old results after switching | Generation guard, await in-flight work, module disposal and overlay reset |
| Late camera permission response | Cancelled/expired acquisition stops any late stream |
| Sign model replacement during inference | Website stops its pipeline before applying; service refuses replacement while another sign lease is active |
| Other tabs unloading the sign model | Browser session identifiers and ownership checks; conflict returns HTTP409 |
| Browser crashes with an active sign lease | Another session can reclaim after 60 seconds without predictions |
| Training versus live sign inference | One training job; sign inference/model switching refused during training; browser face/drawing remain separate |
| Old prediction after profile change | Adapter is closed and result/upload preview are cleared |
| Training replacing existing weights | Existing destination refused; completed temporary model renamed to target |
| Python/native package collisions | Separate repository venv; one OpenCV distribution, pinned legacy MediaPipe stack |

This is still a local workspace with one active sign model/training service.
Browser face/hand inference can run independently in separate tabs, subject to
OS camera permissions and hardware limits; exclusive cross-tab browser webcam
access is not enforced. There is no multi-user hosted inference scheduler.

## Sign dataset and training details

The original contract uses BGR frames; RGB conversion is only for landmark
tracking. Bounding-box padding is 20px, clamped to image bounds; resize is
OpenCV linear interpolation to 64×64, followed by float32 /255. Labels are
A–Z. The original CNN is Conv2D32/64/128 + MaxPooling after each, Flatten,
Dense128, Dropout0.5, Dense26 softmax.

Use **Capture a dataset → Start capture camera → select A–Z → Save sample**.
Capture works without a model, but requires Python OpenCV/NumPy/Pillow.
Samples are mirrored raw frames and use UUID filenames to avoid overwrites.
They are stored in `data/asl_dataset/A` through `Z`. Capture contains no overlay.
Uploaded inference images are used as supplied, matching original behavior.

Built-in training supports **only profiles matching the original contract**.
Other labels, image sizes, color conventions or normalization require a
matching external trainer. This prevents training one architecture under an
unrelated profile. At least five decodable images per letter are required for
the stratified 80/20 split; this is a technical minimum, not a useful accuracy
target. File counts alone do not establish image validity.

Workbench options: 1–100 epochs, batch16/32/64/128, learning rate .0001/.001/.01.
Training keeps the original rotation/zoom/contrast augmentation and early
stopping. Accuracy/loss histories are displayed and saved as
`data/training_history.json`. Completed history is not reloaded into the UI
after a service restart. Training runs in a background thread and cannot
currently be cancelled gracefully; stopping the service terminates it.

## Configuration and API reference

| Configuration | Location / effect |
|---|---|
| Startup sign profile | `config/resources.json: active_sign_profile` |
| Model/resource definitions | `config/resources.json`; refresh/apply as described above |
| Server port | `.env: VISION_PORT`, default8765; restart required |
| Log level | `.env: VISION_LOG_LEVEL`, DEBUG/INFO/WARNING/ERROR |
| Optional interpreter | `.env: VISION_PYTHON`, executable inside the repository |
| Legacy model override | `.env: VISION_MODEL`; original-contract startup only |
| Camera/resolution/FPS/threshold | Website session settings; apply on next camera start |

GET: `/api/health`, `/api/status`, `/api/resources`.
POST JSON: `/api/resources/select` with profile_id; `/api/sign/load` and
`/api/sign/close` with session; `/api/sign/predict` with session/image/threshold;
`/api/dataset/capture` with letter/image; `/api/train` with
epochs/batch_size/learning_rate. The website generates session identifiers.

POST requests require same-origin local Host/Origin and
`X-Vision-Lab: 1`. Images are JPEG/PNG data URLs, limited to 3 MB and
2.1 megapixels; JSON is limited to 4.1 MB. Paths must resolve inside the
repository. Model files are not served as public downloads or accepted as
web uploads. Keep private data outside `frontend/public`, whose files are public
to visitors of the running website.

## Missing, incomplete and unverified items

| Item | Exact state and next action |
|---|---|
| Original trained sign model | **MISSING.** Expected models/sign_language_model.h5; provide your original compatible weights or deliberately train with your own dataset |
| Candidate sign model | **INTENTIONALLY EMPTY.** models/sign-language/candidate/model.keras is a reserved slot, not an included model |
| Original training/evaluation images | **MISSING.** Capture or supply a representative A–Z dataset; no recognition accuracy has been established |
| Native webcam acquisition | **VERIFIED on 2026-10-17.** Camera0 opened, read ten 640×480 frames and was released; no images saved |
| Browser live-module acceptance | **NOT VERIFIED.** Current embedded-browser camera permission timed out; prior access was denied. UI recovered with an actionable message; native acquisition alone does not establish browser face/hand/switching behavior |
| Real sign predictions/accuracy | **NOT VERIFIED.** Native tests use synthetic models/pixels only |
| Python hand tracking on this machine | **NOT VERIFIED.** Installed MediaPipe0.10.32 lacks legacy Solutions; requirements target0.10.21 under Python3.11/3.12 |
| Clean full Python environment | **NOT VERIFIED.** Native tests use existing Python3.13 libraries, not a clean install of the documented pins |
| Model quality/provenance | Face weights/reference came from source folders; upstream version/license provenance is incomplete; no new trained-model download is supplied |
| Runtime compatibility | File/metadata checks do not prove a model will load or predict correctly; load-time shape/probability validation and real evaluation are still required |
| Arbitrary model formats | ONNX/PyTorch/TFLite/temporal/multi-input adapters are not implemented |
| Public hosting | **NOT IMPLEMENTED.** Current deliverable is the complete local website; not an internet deployment or multi-user service |
| Performance | Processed FPS, frame processing ms and Python inference ms are exposed; CPU/memory and sensor-to-display latency are not measured |
| Frontend bundle | face-api chunk remains large and its Node fs branch is externalized; build warnings are documented, not hidden |
| Training lifecycle | No cancellation UI; history files saved but not restored into the workbench after restart |
| Browser ML initialization | Native/WASM initialization still depends on browser GPU/runtime support; camera/API timeouts do not cancel every third-party initialization operation |
| Continuous sign language | Not implemented; static letter classification does not model sequences or motion letters reliably |
| Python dependency reproducibility | Direct versions pinned; full transitive Python lock and Python advisory audit are not supplied |

The source audit is retained in `docs/integration-audit.md`; the final test matrix
is in `docs/verification.md`. Original source hashes are recorded in
`docs/source-baseline.json`. No original folder/history has been deleted or
used as a hidden runtime dependency.

# Troubleshooting

- **Camera timed out / denied / not found:** enable browser/OS camera permission,
  connect a webcam, close competing applications, try Chrome/Edge on localhost,
  then restart the camera. Embedded browsers may not surface permission UI.
  Camera acquisition times out after 15s and releases any late stream.
- **Missing sign model:** place a trusted 64x64 BGR / 26-class A–Z model at
  models/sign_language_model.h5, or set VISION_MODEL to a path inside the repo.
  No weights were included in the supplied Sign Language project.
- **No Python dependencies:** install requirements.txt into a 3.11/3.12 venv.
  Do not blindly install the old projects' overlapping requirement files.
- **Full-frame fallback:** no hand was located or legacy MediaPipe Solutions
  is unavailable. The UI labels this. Check the logs and interpreter/packages;
  the installed 0.10.32 package on this machine has no mp.solutions API.
- **Training split error:** at least five decodable images per A–Z class are
  required. File counts can include corrupt images; decode-time validation
  checks again. Five is a technical minimum, not an accuracy recommendation.
- **Existing model blocks training:** choose a new VISION_MODEL filename in
  .env and restart. Vision-Lab will not overwrite your supplied model.
- **Native failure:** inspect logs/vision-lab.log (rotated), which includes
  detailed backend exceptions. Frontend lifecycle/inference errors appear in
  browser developer console and in an on-screen alert.
- **Port busy:** change VISION_PORT in .env. Do not start duplicate servers.
- **Missing models/MediaPipe assets:** rerun npm ci and npm run build.
  Both public weights and MediaPipe package assets must be in frontend/dist.
- **Large JS chunk warning:** the preserved face-api dependency remains large;
  it is lazy-loaded only for Vision-XE. This is not a failed build.
- **Windows sandbox EPERM during build/tests:** the local build/test tool may
  require permission to spawn compiler/test subprocesses. It does not mean the
  application dependencies are missing.
- **Browser stuck on an older build:** reload after npm run build. No service
  worker or persistent camera session is installed.

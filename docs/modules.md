# Modules and behavior preservation

## Vision-XE

The TinyFaceDetector -> 68 landmarks -> seven face-expression scores chain and
the supplied weight files are reused. Live bars and the last 40 expression
samples are shown while the camera remains active, fixing the old dashboard's
dependency on a separate camera tab. No-face results clear old expression data.

The examination demonstration retains source rules: 3s absence, multiple faces,
nose/eye horizontal ratio >.35, angry/fearful/disgusted/sad >.4, 5s warning
cooldown, three warnings to terminate, optional audio, and reset on restart.
UI labels explicitly describe this as a demonstration. Expression classification
is not a valid basis for determining cheating. The original source still exists.

Result: `detections` (box, detection confidence, expressions, head offset),
`expressions`, `dominant`; when enabled, `warnings` and `terminated`.
No object detection/tracking/pose functionality was present to integrate.

Browser resource URLs/options now come from config/resources.json. Sign models
can use declared size/color/normalization/label contracts via the keras_image
adapter. The original pipeline below describes the default profile; the main
README documents replacements, limitations and supported training contracts.

## Air Write

MediaPipe Hands: complexity1, max two hands, detection .7, tracking .6; first
hand drives drawing. Index raised >.03 draws, index+middle erase, thumb-index
distance <.06 pauses. Exponential smoothing retains .45 previous/.55 new.
The original four-pass neon line rendering, circular eraser size 4x brush,
seven colors, brush2–30, clear, grid, mouse/touch, and keyboard shortcuts remain.
Pinch/no-hand/erase-to-draw transitions no longer connect unrelated strokes.
Pointer mode is an explicit choice and is independent of camera permissions.

Controls: index draw; two fingers erase; pinch pause; E eraser; C clear; G grid;
1–7 colors. Module switching clears the drawing; no drawing persistence or
export was in the original. Resolution changes also clear the canvas.

Result: `gesture`, `coordinates` in mirrored frame pixels, `stroke_active`,
internal segment. MediaPipe assets are pinned and copied into the build, so
runtime does not depend on a third-party CDN.

## Sign Language

This is static ASL alphabet image classification, not a language translator.
The model architecture is a three-convolution CNN, not a landmark-feature
classifier. Landmarks locate a BGR crop; they are not the CNN input.
See models/README.md for precise model and preprocessing requirements.

Modes in the unified UI: live recognition, JPEG/PNG upload with annotation/crop
preview, camera-only raw dataset capture, class counts/reference chart, and
training controls/history. Capture works without a trained model but requires
OpenCV/Pillow. Training is never started automatically. Use diverse examples;
the five-per-class minimum only guarantees a valid split, not a useful model.

Fallback behavior is preserved: without a detected hand or usable MediaPipe,
the whole frame is classified. Every such result has `fallback: true` and the
UI warns about it. Confidence is normalized to [0,1] in the API; original Python
confidence remains [0,100]. Below-threshold predictions are visibly marked.

Result: `label`, `confidence`, `accepted`, `bbox`, normalized `landmarks`,
`fallback`, `inference_ms`. Missing/corrupt/wrong-shape models return clear
errors; there is no dummy recognition mode.

## Migration inventory

Original folders and nested Git histories are preserved unchanged and ignored
by the parent repository. New runnable code has no import dependency on them.
Copied/adapted: face weights, ASL reference, sign detector/dataset, gesture and
drawing formulas, face detection chain, exam rules and analytics behavior.
Replaced in the unified runtime: duplicate camera loops, unbounded intervals,
WebSocket relay/dashboard subscriptions, Streamlit presentation, CDN scripts,
fake splash progress, working-directory-dependent paths. Removed from new
runtime dependencies: Express, cors, ws, React Router, Streamlit, pandas,
matplotlib, unused MediaPipe camera/control utilities. Training charts use SVG;
original matplotlib/Streamlit scripts remain in the source snapshot.

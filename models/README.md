# Model inventory

## Face models

Copied byte-for-byte from the supplied Vision-XE frontend/public/models:
tiny_face_detector, face_landmark_68, face_expression. Each has a JSON weights
manifest and one binary shard. Originals are included in the baseline hash
manifest; copied assets are verified by the asset test. No model download or
retraining was needed. Original source does not record weight provenance or
an upstream checksum/version; do not invent either.

## Air Write

@mediapipe/hands 0.4.1675469240 from npm. Build copies WASM/graph/TFLite/JS
assets into frontend/dist/mediapipe. npm's lockfile integrity records the
package. A network connection is needed at installation, not at inference.

## Sign Language

Expected models/sign_language_model.h5 (Keras HDF5). Native .keras loading is
also possible via VISION_MODEL. No trained file or image dataset was supplied.
There is no verified upstream download URL or checksum. Supply your existing
trusted compatible model; do not download unrelated ASL weights and assume
they share preprocessing/classes. Dataset capture and original CNN training
remain available, but no model was trained during integration.

- Input: float32 batch (N,64,64,3), **BGR**, /255 normalization.
- Tracking: RGB conversion for MediaPipe only; first hand's pixel bounds,
  20px padding, clamped image limits; full-image fallback if no crop.
- Resize: OpenCV default linear interpolation; not RGB/grayscale/landmark input.
- Architecture: Conv32/Conv64/Conv128 (3x3 ReLU), each MaxPool2x2; Flatten;
  Dense128 ReLU; Dropout.5; Dense26 softmax.
- Output: (N,26), index0=A through25=Z. Max softmax score is confidence;
  it is not calibrated probability of correctness.
- Live frames: mirrored to match original OpenCV recognition/capture.
  Uploaded images are used as supplied, matching original upload behavior.

Training writes a complete temporary .h5 and renames it to the configured
target; existing targets are refused. Model files/data are Git-ignored. Keep
your model provenance, evaluation dataset, metrics and SHA256 beside any
distributed model. Motion letters and continuous signing need a different
future dataset/model and are not claimed by this application.

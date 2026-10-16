"""Lazy native dependencies keep the other modules usable without a sign model."""
import base64
import binascii
import logging
import math
import json
import threading
import time
import uuid
from pathlib import Path

from .config import ROOT, local_path

LOG = logging.getLogger(__name__)
LETTERS = tuple(chr(i) for i in range(65, 91))
MAX_IMAGE_BYTES = 3_000_000


def image_bytes(value):
    if not isinstance(value, str) or len(value) > 4_000_100:
        raise ValueError('Image must be a JPEG/PNG data URL under 3 MB.')
    prefix, sep, encoded = value.partition(',')
    if not sep or prefix not in ('data:image/jpeg;base64', 'data:image/png;base64'):
        raise ValueError('Only JPEG and PNG images are accepted.')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError('Invalid base64 image.') from error
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Image is empty or too large.')
    return data


def train_options(body):
    epochs, batch, rate = body.get('epochs', 20), body.get('batch_size', 32), body.get('learning_rate', .001)
    if type(epochs) is not int or not 1 <= epochs <= 100 or type(batch) is not int or batch not in (16, 32, 64, 128):
        raise ValueError('Invalid epochs or batch size.')
    if type(rate) not in (int, float) or rate not in (.0001, .001, .01):
        raise ValueError('Invalid learning rate.')
    return epochs, batch, rate


class SignService:
    def __init__(self, model_path):
        self.model_path = local_path(model_path)
        self.dataset = local_path('data/asl_dataset')
        self.detector = None
        self.lock = threading.RLock()
        self.job = {'state': 'idle', 'history': []}

    def stats(self):
        return {letter: sum(1 for path in (self.dataset / letter).glob('*') if path.suffix.lower() in ('.jpg', '.jpeg', '.png')) for letter in LETTERS}

    def status(self):
        return {'model_exists': self.model_path.is_file(), 'model_loaded': self.detector is not None and self.detector.model is not None,
                'dataset': self.stats(), 'training': self.job}

    def load(self, require_model=True):
        if require_model and not self.model_path.is_file():
            raise ValueError('Sign model missing. Add models/sign_language_model.h5 (or configure VISION_MODEL). No trained model was supplied.')
        if self.detector is None:
            try:
                from .sign.detector import SignLanguageDetector
                detector = SignLanguageDetector(str(self.model_path))
            except ImportError as error:
                raise ValueError('Sign dependencies unavailable. Install requirements.txt in a Python 3.11/3.12 environment.') from error
            self.detector = detector
        if require_model:
            model = self.detector.model
            if model is None:
                self.close()
                raise ValueError('Unable to load sign model. See logs/vision-lab.log.')
            if tuple(model.input_shape[1:]) != (64, 64, 3) or tuple(model.output_shape[1:]) != (26,):
                self.close()
                raise ValueError('Model must accept BGR (64,64,3) and return 26 A–Z probabilities.')
        return self.detector

    @staticmethod
    def decode(value):
        data = image_bytes(value)
        # Read dimensions before native decoding to reject decompression bombs.
        from PIL import Image
        from io import BytesIO
        with Image.open(BytesIO(data)) as image:
            if image.format not in ('JPEG', 'PNG') or image.width * image.height > 2_100_000 or min(image.size) < 16:
                raise ValueError('Image must be JPEG/PNG, at least 16px, and at most 2.1 megapixels.')
            image.verify()
        import cv2
        import numpy as np
        frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError('Could not decode image.')
        return frame

    def predict(self, body):
        threshold = body.get('threshold', .5)
        if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError('Threshold must be between 0 and 1.')
        with self.lock:
            detector = self.load()
            frame = self.decode(body.get('image'))
            start = time.perf_counter()
            result = detector.predict(frame)
            confidence = result['confidence'] / 100
            if not math.isfinite(confidence) or not 0 <= confidence <= 1:
                raise ValueError('Model returned invalid confidence.')
            landmarks = result['landmarks']
            points = [[lm.x, lm.y, lm.z] for hand in (landmarks.multi_hand_landmarks if landmarks else []) for lm in hand.landmark]
            return {'label': result['letter'], 'confidence': confidence, 'accepted': confidence >= threshold,
                    'bbox': result['bbox'], 'landmarks': points, 'fallback': result['bbox'] is None,
                    'inference_ms': (time.perf_counter() - start) * 1000}

    def capture(self, body):
        letter = body.get('letter')
        if letter not in LETTERS:
            raise ValueError('Select a letter A–Z.')
        frame = self.decode(body.get('image'))
        import cv2
        folder = local_path(str(self.dataset / letter))
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f'{uuid.uuid4().hex}.png'
        if not cv2.imwrite(str(path), frame):
            raise ValueError('Unable to save dataset sample.')
        return {'saved': str(path.relative_to(ROOT)), 'dataset': self.stats()}

    def start_training(self, body):
        epochs, batch, rate = train_options(body)
        with self.lock:
            if self.job['state'] == 'running':
                raise ValueError('Training is already running.')
            # 5 per class guarantees enough test slots; decoded counts checked again.
            if any(count < 5 for count in self.stats().values()):
                raise ValueError('Collect at least 5 valid samples for every letter A–Z before training. More diverse samples are strongly recommended.')
            if self.model_path.exists():
                raise ValueError('Training will not overwrite an existing model. Configure a new VISION_MODEL filename and restart.')
            self.job = {'state': 'running', 'epoch': 0, 'epochs': epochs, 'history': []}
            threading.Thread(target=self._train, args=(epochs, batch, rate), daemon=True).start()
        return self.job

    def _train(self, epochs, batch, rate):
        try:
            with self.lock:
                from .sign.dataset import prepare_dataset
                import tensorflow as tf
                detector = self.load(require_model=False)
                train_x, test_x, train_y, test_y = prepare_dataset(str(self.dataset), LETTERS, detector.hands)
                if train_x is None:
                    raise ValueError('No valid training images.')
                detector.build_new_model()
                detector.model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=rate), loss='categorical_crossentropy', metrics=['accuracy'])
                owner = self

                class Progress(tf.keras.callbacks.Callback):
                    def on_epoch_end(self, epoch, logs=None):
                        history = owner.job['history'] + [{key: float(value) for key, value in (logs or {}).items()}]
                        owner.job = {**owner.job, 'epoch': epoch + 1, 'history': history}

                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                # Save only a complete model; interruption leaves the target untouched.
                temporary = self.model_path.with_name(self.model_path.stem + '.tmp' + self.model_path.suffix)
                detector.model_path = str(temporary)
                detector.train(train_x, test_x, train_y, test_y, epochs=epochs, batch_size=batch, callback_list=[Progress()])
                temporary.replace(self.model_path)
                detector.model_path = str(self.model_path)
                loss, accuracy = detector.model.evaluate(test_x, test_y, verbose=0)
                self.job = {**self.job, 'state': 'complete', 'loss': float(loss), 'accuracy': float(accuracy)}
                history_path = local_path('data/training_history.json')
                history_path.parent.mkdir(parents=True, exist_ok=True)
                history_path.write_text(json.dumps(self.job, allow_nan=False), encoding='utf-8')
                LOG.info('Training completed')
        except Exception as error:
            LOG.exception('Training failed')
            self.job = {**self.job, 'state': 'failed', 'error': str(error)}
        finally:
            self.close()

    def close(self):
        with self.lock:
            if self.detector:
                if self.detector.hands:
                    self.detector.hands.close()
                self.detector = None
                try:
                    import tensorflow as tf
                    tf.keras.backend.clear_session()
                except ImportError:
                    pass

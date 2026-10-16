"""Native tests use synthetic pixels/models, never claim recognition accuracy."""
import importlib.util
import base64
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(ROOT / '.cache' / 'matplotlib')
os.environ['KERAS_HOME'] = str(ROOT / '.cache' / 'keras')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
HAS_NATIVE = all(importlib.util.find_spec(module) for module in ('cv2', 'tensorflow', 'numpy', 'sklearn'))


@unittest.skipUnless(HAS_NATIVE, 'Native CNN dependencies unavailable')
class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import numpy as np
        import tensorflow as tf
        from backend.sign import dataset, detector
        cls.np, cls.tf, cls.dataset, cls.detector_module = np, tf, dataset, detector
        (ROOT / '.cache').mkdir(exist_ok=True)

    def test_bgr_resize_normalization(self):
        image = self.np.zeros((100, 120, 3), dtype=self.np.uint8)
        image[:, :, 0] = 255
        actual = self.dataset.preprocess_image(image)
        self.assertEqual(actual.shape, (64, 64, 3))
        self.assertEqual(actual.dtype, self.np.float32)
        self.assertEqual(float(actual[0, 0, 0]), 1.)
        self.assertEqual(float(actual[0, 0, 2]), 0.)
        self.assertIsNone(self.dataset.preprocess_image(None))

    def test_crop_padding_and_rgb_tracking_conversion(self):
        image = self.np.zeros((100, 100, 3), dtype=self.np.uint8)
        image[:, :, 0] = 255
        seen = []
        points = [SimpleNamespace(x=.1, y=.2), SimpleNamespace(x=.8, y=.7)]
        result = SimpleNamespace(multi_hand_landmarks=[SimpleNamespace(landmark=points)])
        hands = SimpleNamespace(process=lambda frame: seen.append(frame.copy()) or result)
        crop, box, _ = self.dataset.detect_and_crop_hand(image, hands)
        self.assertEqual(box, (0, 0, 100, 90))
        self.assertEqual(crop.shape, (90, 100, 3))
        self.assertEqual(int(seen[0][0, 0, 2]), 255)

    def test_synthetic_model_roundtrip_and_prediction_mapping(self):
        # Known output Z validates mapping/preprocessing; this is NOT a trained model.
        from backend.service import SignService
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            path = Path(folder) / 'synthetic.h5'
            inputs = self.tf.keras.Input((64, 64, 3))
            pooled = self.tf.keras.layers.GlobalAveragePooling2D()(inputs)
            dense = self.tf.keras.layers.Dense(26, activation='softmax', kernel_initializer='zeros')(pooled)
            model = self.tf.keras.Model(inputs, dense)
            weights, bias = model.layers[-1].get_weights()
            bias[25] = 10
            model.layers[-1].set_weights([weights, bias])
            model.save(path)
            service = SignService(path)
            with patch.object(self.detector_module, 'HAS_MEDIAPIPE', False):
                detector = service.load()
            prediction = detector.predict(self.np.zeros((80, 80, 3), dtype=self.np.uint8))
            self.assertEqual(prediction['letter'], 'Z')
            self.assertGreater(prediction['confidence'], 99)
            self.assertIsNone(prediction['bbox'])
            import cv2
            _, encoded = cv2.imencode('.png', self.np.zeros((80, 80, 3), dtype=self.np.uint8))
            result = service.predict({'image': 'data:image/png;base64,' + base64.b64encode(encoded).decode(), 'threshold': .5})
            self.assertEqual(result['label'], 'Z')
            self.assertTrue(result['accepted'])
            self.assertTrue(result['fallback'])
            self.assertGreater(result['confidence'], .99)
            self.assertLessEqual(result['confidence'], 1.)
            service.close()
            self.assertIsNone(service.detector)

    def test_invalid_model_shape(self):
        from backend.service import SignService
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            path = Path(folder) / 'bad.h5'
            model = self.tf.keras.Sequential([self.tf.keras.Input((4,)), self.tf.keras.layers.Dense(2)])
            model.save(path)
            with patch.object(self.detector_module, 'HAS_MEDIAPIPE', False):
                service = SignService(path)
                with self.assertRaisesRegex(ValueError, '64,64,3'):
                    service.load()
            self.assertIsNone(service.detector)

    def test_corrupt_model(self):
        from backend.service import SignService
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            path = Path(folder) / 'bad.h5'
            path.write_bytes(b'not a model')
            with patch.object(self.detector_module, 'HAS_MEDIAPIPE', False):
                service = SignService(path)
                with self.assertRaisesRegex(ValueError, 'Unable to load'):
                    service.load()

    def test_original_cnn_training_smoke(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            with patch.object(self.detector_module, 'HAS_MEDIAPIPE', False):
                detector = self.detector_module.SignLanguageDetector(str(Path(folder) / 'smoke.h5'))
            detector.build_new_model()
            self.assertEqual(detector.model.input_shape, (None, 64, 64, 3))
            self.assertEqual(detector.model.output_shape, (None, 26))
            images = self.np.zeros((4, 64, 64, 3), dtype=self.np.float32)
            labels = self.tf.keras.utils.to_categorical([0, 1, 0, 1], 26)
            history = detector.train(images, images[:2], labels, labels[:2], epochs=1, batch_size=2)
            self.assertTrue(self.np.isfinite(history.history['loss'][0]))
            self.assertTrue(Path(detector.model_path).is_file())

    def test_replacement_profile_changes_size_color_and_labels(self):
        import cv2
        from backend.resources import ResourceCatalog, original_profile
        from backend.service import SignService
        import json
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as folder:
            folder = Path(folder)
            path = folder / 'replacement.keras'
            inputs = self.tf.keras.Input((80, 96, 3))
            pool = self.tf.keras.layers.GlobalAveragePooling2D()(inputs)
            output = self.tf.keras.layers.Dense(2, activation='softmax')(pool)
            model = self.tf.keras.Model(inputs, output)
            model.layers[-1].set_weights([self.np.array([[3., -3.], [0., 0.], [-3., 3.]], dtype=self.np.float32), self.np.zeros(2, dtype=self.np.float32)])
            model.save(path)
            profile = original_profile(str(path))
            profile.update(id='replacement', name='Synthetic RGB replacement', labels=['red', 'blue'])
            profile['input'].update(width=96, height=80, color='RGB')
            profile['hand_crop']['enabled'] = False
            catalog_data = ResourceCatalog().read()
            catalog_data.update(active_sign_profile='replacement', sign_profiles=[profile])
            catalog_path = folder / 'resources.json'
            catalog_path.write_text(json.dumps(catalog_data), encoding='utf-8')
            service = SignService(catalog=ResourceCatalog(catalog_path))
            image = self.np.zeros((40, 40, 3), dtype=self.np.uint8)
            image[:, :, 0] = 255
            _, encoded = cv2.imencode('.png', image)
            result = service.predict({'image': 'data:image/png;base64,' + base64.b64encode(encoded).decode()})
            self.assertEqual(result['label'], 'blue')
            self.assertEqual(result['profile_id'], 'replacement')
            self.assertFalse(result['fallback'])
            service.close()


if __name__ == '__main__':
    unittest.main()

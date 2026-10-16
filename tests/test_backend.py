import base64
import json
import os
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer

from backend.config import ROOT, local_path, settings
from backend.service import SignService, image_bytes, train_options
from backend.server import Handler


class ConfigurationTests(unittest.TestCase):
    def test_paths_cannot_escape_workspace(self):
        self.assertEqual(local_path('models/test.h5'), ROOT / 'models' / 'test.h5')
        with self.assertRaises(ValueError):
            local_path('../outside.h5')

    def test_bad_config(self):
        with patch.dict(os.environ, {'VISION_PORT': '0'}):
            with self.assertRaises(ValueError):
                settings()

    def test_payload_validation(self):
        for image in (None, '', 'data:text/plain;base64,YQ==', 'data:image/png;base64,@@@'):
            with self.assertRaises(ValueError):
                image_bytes(image)
        self.assertEqual(image_bytes('data:image/png;base64,YQ=='), b'a')
        for body in ({'epochs': 0}, {'epochs': True}, {'batch_size': 7}, {'learning_rate': 2}):
            with self.assertRaises(ValueError):
                train_options(body)

    def test_missing_model_does_not_import_native_dependencies(self):
        service = SignService('models/not-supplied.h5')
        with self.assertRaisesRegex(ValueError, 'missing'):
            service.load()
        self.assertIsNone(service.detector)

    def test_training_rejects_insufficient_data(self):
        service = SignService('models/not-supplied.h5')
        with patch.object(service, 'stats', return_value={chr(i): 0 for i in range(65, 91)}):
            with self.assertRaisesRegex(ValueError, '5 valid'):
                service.start_training({})


class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.server.service = SignService('models/not-supplied.h5')
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, body=None, headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        connection.request('GET' if body is None else 'POST', path, body, headers or {})
        response = connection.getresponse()
        result = response.status, json.loads(response.read())
        connection.close()
        return result

    def test_health_and_missing_model(self):
        self.assertEqual(self.request('/api/health')[0], 200)
        status, body = self.request('/api/sign/load', '{"session":"test-client"}', {'Content-Type': 'application/json', 'X-Vision-Lab': '1'})
        self.assertEqual(status, 400)
        self.assertIn('missing', body['error'])

    def test_rejects_foreign_origin_and_host(self):
        self.assertEqual(self.request('/api/health', headers={'Origin': 'https://example.com'})[0], 403)
        self.assertEqual(self.request('/api/health', headers={'Host': 'evil.test'})[0], 403)
        self.assertEqual(self.request('/api/sign/close', '{}')[0], 403)

    def test_traversal_and_malformed_body(self):
        self.assertEqual(self.request('/%2e%2e/package.json')[0], 403)
        self.assertEqual(self.request('/api/sign/load', '[1]', {'Content-Type': 'application/json', 'X-Vision-Lab': '1'})[0], 400)

    def test_resource_status_and_model_selection(self):
        code, body = self.request('/api/resources')
        self.assertEqual(code, 200)
        self.assertIn('profiles', body)
        headers = {'Content-Type': 'application/json', 'X-Vision-Lab': '1'}
        code, body = self.request('/api/resources/select', '{"profile_id":"asl-candidate"}', headers)
        self.assertEqual(code, 200)
        self.assertEqual(body['profile']['id'], 'asl-candidate')
        self.assertFalse(body['model_exists'])
        self.request('/api/resources/select', '{"profile_id":"asl-original"}', headers)


try:
    import cv2
    import numpy as np
    HAS_CV = True
except ImportError:
    HAS_CV = False


@unittest.skipUnless(HAS_CV, 'OpenCV/NumPy unavailable')
class ImageTests(unittest.TestCase):
    def test_decode_preserves_bgr_and_rejects_invalid_image(self):
        image = np.zeros((32, 32, 3), dtype=np.uint8)
        image[:, :, 0] = 255
        ok, encoded = cv2.imencode('.png', image)
        self.assertTrue(ok)
        decoded = SignService.decode('data:image/png;base64,' + base64.b64encode(encoded).decode())
        np.testing.assert_array_equal(image, decoded)
        with self.assertRaises(Exception):
            SignService.decode('data:image/png;base64,YQ==')


if __name__ == '__main__':
    unittest.main()

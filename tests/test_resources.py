from copy import deepcopy
import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.config import ROOT
from backend.resources import ResourceCatalog, asset_path, original_profile, validate_profile, original_training_supported
from backend.service import SignService, ResourceBusy


class ResourceTests(unittest.TestCase):
    def test_default_catalog_and_empty_slots(self):
        service = SignService()
        report = service.catalog.report(service)
        self.assertEqual(report['active_sign_profile'], 'asl-original')
        self.assertEqual(len(report['profiles']), 2)
        self.assertFalse(report['profiles'][0]['ready'])
        self.assertTrue(any('missing' in issue.lower() for issue in report['profiles'][0]['issues']))
        self.assertEqual(service.profile['labels'][0], 'A')

    def test_missing_labels_and_bad_contract_are_actionable(self):
        value = original_profile('models/test.h5')
        value['labels_path'] = 'models/missing-labels.json'
        with self.assertRaisesRegex(ValueError, 'Labels missing'):
            validate_profile(value)
        value.pop('labels_path')
        value['input']['color'] = 'GRAY'
        with self.assertRaisesRegex(ValueError, 'BGR or RGB'):
            validate_profile(value)

    def test_paths_and_unique_labels(self):
        for url in ('https://example.com/a', '//evil/a', '/models/../secret', '/%2e%2e/a', '/models/a?x=1'):
            with self.assertRaises(ValueError):
                asset_path(url)
        profile = original_profile('../outside.h5')
        with self.assertRaises(ValueError):
            validate_profile(profile)
        profile = original_profile('models/test.h5')
        profile['labels'] = ['A', 'A']
        with self.assertRaisesRegex(ValueError, 'unique'):
            validate_profile(profile)

    def test_switch_validates_before_disposing_and_allows_empty_model_slot(self):
        service = SignService()
        old = service.profile
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            service.select_profile('unknown')
        self.assertEqual(service.profile, old)
        service.select_profile('asl-candidate')
        self.assertEqual(service.profile['id'], 'asl-candidate')
        with self.assertRaisesRegex(ValueError, 'missing'):
            service.load()

    def test_custom_contract_disables_original_training(self):
        profile = original_profile('models/custom.keras')
        profile['labels'] = ['yes', 'no']
        profile['input'].update(width=96, height=80, color='RGB', scale=1 / 127.5, offset=-1)
        self.assertFalse(original_training_supported(validate_profile(profile)))
        service = SignService()
        service.profile = profile
        with self.assertRaisesRegex(ValueError, 'external trainer'):
            service.start_training({})

    def test_browser_session_cannot_close_or_replace_another_owner(self):
        service = SignService()
        with patch.object(service, 'load', return_value=SimpleNamespace()):
            service.acquire('browser-a')
            with self.assertRaises(ResourceBusy):
                service.acquire('browser-b')
            with self.assertRaises(ResourceBusy):
                service.release('browser-b')
            with self.assertRaises(ResourceBusy):
                service.select_profile('asl-candidate')
            self.assertEqual(service.owner, 'browser-a')
            service.release('browser-a')
            service.acquire('browser-b')
            self.assertEqual(service.owner, 'browser-b')

    def test_abandoned_session_can_be_reclaimed(self):
        service = SignService()
        with patch.object(service, 'load', return_value=SimpleNamespace()):
            service.acquire('old')
            service.last_seen = time.monotonic() - 61
            service.acquire('new')
            self.assertEqual(service.owner, 'new')

    def test_config_failure_returns_ui_diagnostics_without_native_imports(self):
        catalog = ResourceCatalog()
        service = SignService(catalog=catalog)
        with patch.object(catalog, 'read', side_effect=ValueError('Malformed catalog')):
            self.assertIn('Malformed', catalog.report(service)['error'])

    def test_training_blocks_profile_switch(self):
        service = SignService()
        service.job['state'] = 'running'
        with self.assertRaisesRegex(ValueError, 'during training'):
            service.select_profile('asl-candidate')

    def test_unsupported_adapter_isolated(self):
        from backend.model_adapters import load_adapter
        profile = original_profile('models/custom.onnx')
        profile['adapter'] = 'onnx_future'
        profile = validate_profile(profile)
        with self.assertRaisesRegex(ValueError, 'Unsupported model adapter'):
            load_adapter(profile)

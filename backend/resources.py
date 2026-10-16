"""Editable resource catalog. Inspect metadata without importing native ML libraries."""
from copy import deepcopy
import importlib.util
from importlib import metadata
import json
import math
import re
from pathlib import PurePosixPath

from .config import ROOT, local_path

DEFAULT_LABELS = [chr(i) for i in range(65, 91)]


def original_profile(path):
    return {
        'id': 'asl-original', 'name': 'Original ASL CNN', 'adapter': 'keras_image',
        'path': str(path), 'labels': DEFAULT_LABELS.copy(),
        'input': {'width': 64, 'height': 64, 'color': 'BGR', 'scale': 1 / 255, 'offset': 0},
        'hand_crop': {'enabled': True, 'padding': 20, 'no_hand': 'full_frame'},
    }


def validate_profile(value):
    """Validate a contract without loading weights; absent labels are a resource error."""
    if not isinstance(value, dict):
        raise ValueError('Each model profile must be a JSON object.')
    profile = deepcopy(value)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', profile.get('id', '')):
        raise ValueError('Profile id must be a short lowercase identifier.')
    if not isinstance(profile.get('name'), str) or not profile['name'].strip():
        raise ValueError('Profile name is required.')
    path = local_path(profile.get('path', ''))
    if profile.get('adapter') == 'keras_image' and path.suffix.lower() not in ('.h5', '.keras'):
        raise ValueError('keras_image profiles require an .h5 or .keras path.')
    spec = profile.get('input', {})
    if not isinstance(spec, dict):
        raise ValueError('Profile input must be a JSON object.')
    for key in ('width', 'height'):
        if type(spec.get(key)) is not int or not 16 <= spec[key] <= 1024:
            raise ValueError(f'Input {key} must be an integer from 16 to 1024.')
    if spec.get('color') not in ('BGR', 'RGB'):
        raise ValueError('Input color must be BGR or RGB.')
    for key in ('scale', 'offset'):
        if type(spec.get(key)) not in (float, int) or not math.isfinite(spec[key]):
            raise ValueError(f'Input {key} must be finite.')
    if spec['scale'] == 0:
        raise ValueError('Input scale cannot be zero.')
    crop = profile.get('hand_crop', {})
    if not isinstance(crop, dict):
        raise ValueError('Profile hand_crop must be a JSON object.')
    if type(crop.get('enabled')) is not bool or type(crop.get('padding')) is not int or not 0 <= crop['padding'] <= 256:
        raise ValueError('Hand crop needs enabled (boolean) and padding (0–256).')
    if crop.get('no_hand') not in ('full_frame', 'skip'):
        raise ValueError('hand_crop.no_hand must be full_frame or skip.')
    if 'labels_path' in profile:
        label_path = local_path(profile['labels_path'])
        if not label_path.is_file():
            raise ValueError(f'Labels missing: {profile["labels_path"]}. Add a JSON array in output-index order.')
        profile['labels'] = json.loads(label_path.read_text(encoding='utf-8-sig'))
    labels = profile.get('labels')
    if not isinstance(labels, list) or not 2 <= len(labels) <= 1000 or any(not isinstance(label, str) or not label.strip() or len(label) > 100 for label in labels):
        raise ValueError('Labels must be 2–1000 nonempty strings.')
    if len(labels) != len(set(labels)):
        raise ValueError('Labels must be unique and in model-output order.')
    return profile


def original_training_supported(profile):
    spec, crop = profile['input'], profile['hand_crop']
    return (profile['adapter'] == 'keras_image' and profile['labels'] == DEFAULT_LABELS
            and spec['width'] == spec['height'] == 64 and spec['color'] == 'BGR'
            and math.isclose(spec['scale'], 1 / 255) and spec['offset'] == 0
            and crop == {'enabled': True, 'padding': 20, 'no_hand': 'full_frame'})


def asset_path(url):
    if not isinstance(url, str) or not url.startswith('/') or url.startswith('//') or any(c in url for c in ('?', '#', chr(92), '%')):
        raise ValueError('Asset URL must be a local absolute path, e.g. /models/my-model.')
    if '..' in PurePosixPath(url).parts:
        raise ValueError('Asset URL cannot contain traversal.')
    path = local_path('frontend/dist/' + url.lstrip('/'))
    if not path.is_relative_to((ROOT / 'frontend/dist').resolve()):
        raise ValueError('Asset must remain inside the built website.')
    return path


class ResourceCatalog:
    def __init__(self, path=None):
        self.path = local_path(path or 'config/resources.json')

    def read(self):
        try:
            value = json.loads(self.path.read_text(encoding='utf-8-sig'))
            if value.get('version') != 1 or not isinstance(value.get('sign_profiles'), list):
                raise ValueError('Expected version 1 and a sign_profiles array.')
            ids = [p['id'] for p in value['sign_profiles']]
            if len(ids) != len(set(ids)):
                raise ValueError('Duplicate sign profile ids.')
            return value
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f'Resource catalog unavailable: {error}. Fix config/resources.json and refresh resources.') from error

    def profile(self, profile_id):
        for value in self.read()['sign_profiles']:
            if value.get('id') == profile_id:
                return validate_profile(value)
        raise ValueError(f'Unknown sign profile: {profile_id}.')

    def report(self, service):
        try:
            catalog = self.read()
        except ValueError as error:
            return {'error': str(error), 'profiles': [], 'modules': {}, 'active_sign_profile': service.profile['id']}
        from .model_adapters import ADAPTERS
        profiles = []
        dependencies = [name for name in ('tensorflow', 'cv2', 'numpy', 'PIL') if importlib.util.find_spec(name) is None]
        for value in catalog['sign_profiles']:
            if value.get('id') == service.profile['id'] and not service.profile_error:
                # Active contract is a snapshot until explicitly applied again.
                value = {**value, **service.profile}
            entry = {key: value.get(key) for key in ('id', 'name', 'path', 'labels_path', 'adapter', 'description')}
            issues = []
            try:
                profile = validate_profile(value)
                if profile['adapter'] not in ADAPTERS:
                    issues.append(f'Adapter "{profile["adapter"]}" is not implemented. Register it in backend/model_adapters.py.')
                model = local_path(profile['path'])
                if not model.is_file() or model.stat().st_size == 0:
                    issues.append(f'Model missing or empty: {profile["path"]}. Place real trained weights here; no placeholder predictions are generated.')
                entry.update(input=profile['input'], labels=profile['labels'], hand_crop=profile['hand_crop'],
                             training_supported=original_training_supported(profile))
            except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
                issues.append(str(error))
            if dependencies:
                issues.append('Python dependencies missing: ' + ', '.join(dependencies) + '. Install requirements.txt with Python 3.11/3.12.')
            entry.update(ready=not issues, issues=issues, validation='Metadata/files only; model compatibility is checked on load.')
            profiles.append(entry)
        modules = {}
        for name, inspect in (('vision_xe', self.face_config), ('air_write', self.air_config)):
            try:
                config = inspect()
                modules[name] = {'ready': True, 'issues': [], 'config': config}
            except (ValueError, OSError, TypeError, KeyError, AttributeError) as error:
                modules[name] = {'ready': False, 'issues': [str(error)]}
        active = next((p for p in profiles if p['id'] == service.profile['id']), None)
        modules['sign_language'] = {'ready': bool(active and active['ready'] and not service.profile_error),
                                    'issues': active['issues'] if active else ['Active profile is not in the catalog. Select a valid profile.']}
        if service.profile_error:
            modules['sign_language']['issues'] = [service.profile_error] + modules['sign_language']['issues']
        reference = catalog.get('reference_image')
        try:
            reference_ready = asset_path(reference).is_file()
        except (ValueError, TypeError):
            reference_ready = False
        warnings = []
        try:
            files = metadata.files('mediapipe') or []
            if not any(str(path).replace(chr(92), '/').endswith('python/solutions/hands.py') for path in files):
                warnings.append('Legacy Python MediaPipe Hands is unavailable in this installation. Sign hand cropping may fall back or skip; use the documented Python 3.11/3.12 requirements.')
        except metadata.PackageNotFoundError:
            warnings.append('Python MediaPipe is missing. Sign hand cropping is unavailable; Air Write uses its independent browser runtime.')
        if importlib.util.find_spec('sklearn') is None:
            warnings.append('scikit-learn is missing. Built-in sign training needs requirements.txt.')
        return {'profiles': profiles, 'modules': modules, 'active_sign_profile': service.profile['id'],
                'reference': {'url': reference if reference_ready else None, 'ready': reference_ready,
                              'issue': None if reference_ready else 'Optional ASL reference image missing. Set reference_image in config/resources.json and rebuild.'},
                'training': service.job['state'], 'warnings': warnings}

    def face_config(self):
        config = self.read().get('vision_xe', {})
        if config.get('adapter') != 'face_api':
            raise ValueError('Vision-XE adapter unavailable. Implement/register a browser adapter before changing model families.')
        for name in ('tiny_face_detector', 'face_landmark_68', 'face_expression'):
            url = config.get('models', {}).get(name)
            directory = asset_path(url)
            manifest_path = directory / f'{name}_model-weights_manifest.json'
            if not manifest_path.is_file():
                raise ValueError(f'Face model missing: {url}/{manifest_path.name}. Add the matching manifest/shards to frontend/public and rebuild.')
            try:
                manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
                if not isinstance(manifest, list) or not manifest:
                    raise ValueError('Empty weights manifest.')
                for group in manifest:
                    if not group['paths']:
                        raise ValueError('Empty shard list.')
                    for shard in group['paths']:
                        path = (directory / shard).resolve()
                        if not path.is_relative_to(directory.resolve()) or not path.is_file() or path.stat().st_size == 0:
                            raise ValueError(f'Missing or invalid model shard: {shard}')
            except (ValueError, OSError, KeyError, TypeError) as error:
                raise ValueError(f'Invalid face model at {url}: {error}') from error
        return config

    def air_config(self):
        config = self.read().get('air_write', {})
        if config.get('adapter') != 'mediapipe_hands':
            raise ValueError('Air Write adapter unavailable. Implement/register a browser adapter before changing hand-model families.')
        folder = asset_path(config.get('asset_base'))
        required = ('hands.js', 'hands.binarypb', 'hand_landmark_full.tflite', 'hand_landmark_lite.tflite',
                    'hands_solution_packed_assets.data', 'hands_solution_packed_assets_loader.js',
                    'hands_solution_simd_wasm_bin.js', 'hands_solution_simd_wasm_bin.wasm',
                    'hands_solution_simd_wasm_bin.data', 'hands_solution_wasm_bin.js', 'hands_solution_wasm_bin.wasm')
        missing = [name for name in required if not (folder / name).is_file() or (folder / name).stat().st_size == 0]
        if missing:
            raise ValueError('Hand tracking resources missing: ' + ', '.join(missing) + '. Run npm ci and npm run build, or correct air_write.asset_base.')
        options = config.get('options', {})
        if options.get('maxNumHands') not in (1, 2) or options.get('modelComplexity') not in (0, 1):
            raise ValueError('Hand options require maxNumHands 1/2 and modelComplexity 0/1.')
        for key in ('minDetectionConfidence', 'minTrackingConfidence'):
            if type(options.get(key)) not in (float, int) or not 0 <= options[key] <= 1:
                raise ValueError(f'Invalid hand option {key}.')
        return config

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def local_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError('Configured path must remain inside Vision-Lab.')
    return path


def load_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                key, sep, value = line.partition('=')
                if not sep or not key.startswith('VISION_'):
                    raise ValueError('Invalid .env entry; use VISION_NAME=value.')
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def settings():
    load_env()
    port = int(os.environ.get('VISION_PORT', '8765'))
    if not 1024 <= port <= 65535:
        raise ValueError('VISION_PORT must be between 1024 and 65535.')
    level = os.environ.get('VISION_LOG_LEVEL', 'INFO').upper()
    if level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR'):
        raise ValueError('Invalid VISION_LOG_LEVEL.')
    model = local_path(os.environ.get('VISION_MODEL', 'models/sign_language_model.h5'))
    if model.suffix.lower() not in ('.h5', '.keras'):
        raise ValueError('VISION_MODEL must use .h5 or .keras format.')
    return {'port': port, 'model': model, 'log_level': level}

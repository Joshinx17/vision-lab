"""Trusted factories. A config string never becomes an import or eval."""


def keras_image(profile):
    from .sign.detector import SignLanguageDetector
    from .config import local_path
    spec, crop = profile['input'], profile['hand_crop']
    detector = SignLanguageDetector(
        str(local_path(profile['path'])), input_size=(spec['width'], spec['height']),
        letters=profile['labels'], color_order=spec['color'], scale=spec['scale'],
        offset=spec['offset'], crop_enabled=crop['enabled'], padding=crop['padding'],
        no_hand=crop['no_hand'],
    )
    try:
        if detector.model is None:
            raise ValueError('Unable to load sign model. See logs/vision-lab.log.')
        expected = (spec['height'], spec['width'], 3)
        if tuple(detector.model.input_shape[1:]) != expected or tuple(detector.model.output_shape[1:]) != (len(profile['labels']),):
            raise ValueError(f'Model must accept {spec["color"]} ({spec["height"]},{spec["width"]},3) and return {len(profile["labels"])} probabilities. Fix the selected profile contract.')
        return detector
    except Exception:
        detector.close()
        raise


ADAPTERS = {'keras_image': keras_image}


def load_adapter(profile):
    factory = ADAPTERS.get(profile['adapter'])
    if factory is None:
        raise ValueError(f'Unsupported model adapter: {profile["adapter"]}. Add a factory to backend/model_adapters.py.')
    return factory(profile)

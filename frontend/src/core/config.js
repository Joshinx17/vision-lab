export const defaults = Object.freeze({ width: 640, height: 480, fps: 15, deviceId: '', confidence: 0.5 });
export function validateConfig(value) {
  const config = { ...defaults, ...value };
  for (const [key, min, max] of [['width', 160, 1920], ['height', 120, 1080], ['fps', 1, 60]]) {
    if (!Number.isInteger(config[key]) || config[key] < min || config[key] > max) throw new Error(`Invalid ${key}: expected ${min}–${max}.`);
  }
  if (!Number.isFinite(config.confidence) || config.confidence < 0 || config.confidence > 1) throw new Error('Confidence must be between 0 and 1.');
  return config;
}

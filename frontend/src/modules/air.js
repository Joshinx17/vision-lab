import { gesture, Stroke, paint, erase } from './air-logic.js';
import { moduleResources } from '../core/resources.js';
let scriptReady;
let loadedBase;
function loadHands(base) {
  if (loadedBase && loadedBase !== base) throw new Error('Hand runtime path changed. Reload this webpage to activate the replacement assets.');
  if (window.Hands) return Promise.resolve();
  if (!scriptReady) scriptReady = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    loadedBase = base;
    script.src = base + '/hands.js';
    script.onload = resolve;
    script.onerror = () => { script.remove(); scriptReady = null; reject(new Error('Hand tracking assets missing. Run npm run build.')); };
    document.head.appendChild(script);
  });
  return scriptReady;
}
export class AirWrite {
  id = 'air_write';
  constructor(options) { this.options = options; this.stroke = new Stroke(); }
  async initialize({ canvas }) {
    this.canvas = canvas;
    const resources = await moduleResources(this.id);
    await loadHands(resources.asset_base);
    this.hands = new window.Hands({ locateFile: file => resources.asset_base + '/' + file });
    this.hands.setOptions(resources.options);
    this.hands.onResults(results => { this.landmarks = results.multiHandLandmarks?.[0]; });
    await this.hands.initialize();
  }
  async process(frame) {
    this.landmarks = null;
    await this.hands.send({ image: frame });
    const mode = gesture(this.landmarks, this.options.current.eraser);
    const point = this.landmarks ? [this.landmarks[8].x * frame.width, this.landmarks[8].y * frame.height] : null;
    const segment = this.stroke.update(point, mode);
    return { gesture: mode, coordinates: this.stroke.point, stroke_active: mode === 'draw', segment };
  }
  render(result, canvas) {
    const { color, size } = this.options.current;
    const ctx = canvas.getContext('2d');
    if (result.segment) paint(ctx, result.segment, color, size);
    if (result.gesture === 'erase' && result.coordinates) erase(ctx, result.coordinates, size);
  }
  clear() { this.canvas.getContext('2d').clearRect(0, 0, this.canvas.width, this.canvas.height); this.stroke.reset(); }
  async dispose() { await this.hands?.close(); this.stroke.reset(); }
}

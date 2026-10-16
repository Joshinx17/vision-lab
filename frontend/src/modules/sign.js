import { api } from '../core/api.js';
export class SignLanguage {
  id = 'sign_language';
  constructor() { this.session = crypto.randomUUID(); }
  async initialize({ config }) {
    this.config = config;
    await api('sign/load', { session: this.session });
  }
  async process(frame) {
    return api('sign/predict', { image: frame.toDataURL('image/jpeg', .9), threshold: this.config.confidence, session: this.session });
  }
  render(result, canvas) {
    const ctx = canvas.getContext('2d'); ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#63f2be'; ctx.lineWidth = 2;
    if (result.bbox) { const [x, y, right, bottom] = result.bbox; ctx.strokeRect(x, y, right - x, bottom - y); }
    for (const point of result.landmarks ?? []) { ctx.beginPath(); ctx.arc(point[0] * canvas.width, point[1] * canvas.height, 3, 0, 2 * Math.PI); ctx.stroke(); }
    ctx.fillStyle = '#ffffff'; ctx.font = '20px sans-serif';
    ctx.fillText(result.skipped ? 'No hand detected · prediction skipped' : `${result.accepted ? result.label : 'Low confidence'} · ${(result.confidence * 100).toFixed(1)}%`, 16, 32);
  }
  async dispose() {
    try { await api('sign/close', { session: this.session }); }
    catch (error) { console.warn('Sign session cleanup:', error.message); }
  }
}

import { api } from '../core/api.js';
export class SignLanguage {
  id = 'sign_language';
  async initialize({ config }) {
    this.config = config;
    await api('sign/load', {});
  }
  async process(frame) {
    return api('sign/predict', { image: frame.toDataURL('image/jpeg', .9), threshold: this.config.confidence });
  }
  render(result, canvas) {
    const ctx = canvas.getContext('2d'); ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#63f2be'; ctx.lineWidth = 2;
    if (result.bbox) { const [x, y, right, bottom] = result.bbox; ctx.strokeRect(x, y, right - x, bottom - y); }
    for (const point of result.landmarks ?? []) { ctx.beginPath(); ctx.arc(point[0] * canvas.width, point[1] * canvas.height, 3, 0, 2 * Math.PI); ctx.stroke(); }
    ctx.fillStyle = '#ffffff'; ctx.font = '20px sans-serif';
    ctx.fillText(`${result.accepted ? result.label : 'Low confidence'} · ${(result.confidence * 100).toFixed(1)}%`, 16, 32);
  }
  async dispose() { await api('sign/close', {}); }
}

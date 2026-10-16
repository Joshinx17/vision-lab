export const COLORS = ['#00ffff', '#ff00ff', '#39ff14', '#ffff00', '#ff6600', '#ff1493', '#007fff'];
export function gesture(landmarks, forceErase = false) {
  if (!landmarks?.length) return 'no-hand';
  const index = landmarks[8], thumb = landmarks[4];
  if (Math.hypot(thumb.x - index.x, thumb.y - index.y) < 0.06) return 'pause';
  const extended = index.y < landmarks[6].y - 0.03;
  if (forceErase || (extended && landmarks[12].y < landmarks[10].y - 0.03)) return 'erase';
  return extended ? 'draw' : 'hover';
}
export class Stroke {
  constructor() { this.reset(); }
  reset() { this.point = null; this.previous = null; this.mode = null; }
  update(point, mode) {
    if (!point) { this.reset(); return null; }
    this.point = this.point ? this.point.map((v, i) => v + (point[i] - v) * 0.55) : point;
    const segment = mode === 'draw' && this.mode === 'draw' && this.previous ? [this.previous, this.point] : null;
    this.previous = mode === 'draw' ? [...this.point] : null;
    this.mode = mode;
    return segment;
  }
}
export function paint(ctx, segment, color, size) {
  ctx.save();
  ctx.globalCompositeOperation = 'source-over';
  ctx.lineCap = ctx.lineJoin = 'round';
  for (const [width, alpha, blur, ink] of [[size + 10, .08, 30, color], [size + 4, .2, 20, color], [size, 1, 15, color], [Math.max(1, size * .3), .6, 0, '#ffffff']]) {
    ctx.strokeStyle = ctx.shadowColor = ink;
    ctx.lineWidth = width; ctx.globalAlpha = alpha; ctx.shadowBlur = blur;
    ctx.beginPath(); ctx.moveTo(...segment[0]); ctx.lineTo(...segment[1]); ctx.stroke();
  }
  ctx.restore();
}
export function erase(ctx, point, size) {
  ctx.save(); ctx.globalCompositeOperation = 'destination-out';
  ctx.beginPath(); ctx.arc(...point, size * 2, 0, Math.PI * 2); ctx.fill(); ctx.restore();
}

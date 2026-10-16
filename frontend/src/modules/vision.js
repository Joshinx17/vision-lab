import { ExamRules } from './exam-rules.js';
import { moduleResources } from '../core/resources.js';
export class VisionXE {
  id = 'vision_xe';
  constructor(options) { this.options = options; this.rules = new ExamRules(); }
  async initialize() {
    const resources = await moduleResources(this.id);
    this.faceapi = await import('face-api.js');
    const { nets } = this.faceapi;
    await Promise.all([
      nets.tinyFaceDetector.loadFromUri(resources.models.tiny_face_detector),
      nets.faceLandmark68Net.loadFromUri(resources.models.face_landmark_68),
      nets.faceExpressionNet.loadFromUri(resources.models.face_expression),
    ]);
  }
  async process(frame) {
    const f = this.faceapi;
    this.detections = await f.detectAllFaces(frame, new f.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceExpressions();
    const detections = this.detections.map(d => {
      const left = d.landmarks.getLeftEye()[0], right = d.landmarks.getRightEye()[3], nose = d.landmarks.getNose()[3];
      return { box: d.detection.box, confidence: d.detection.score, expressions: { ...d.expressions }, offset: Math.abs(nose.x - (left.x + right.x) / 2) / Math.max(1, Math.abs(right.x - left.x)) };
    });
    const expressions = detections[0]?.expressions ?? {};
    const dominant = Object.entries(expressions).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null;
    const exam = this.options.current.exam ? this.rules.evaluate(detections, Date.now()) : {};
    if (!this.options.current.exam) this.rules = new ExamRules();
    if (exam.issued) this.alarm(exam.terminated);
    return { detections, expressions, dominant, ...exam };
  }
  render(_result, canvas) {
    const ctx = canvas.getContext('2d'); ctx.clearRect(0, 0, canvas.width, canvas.height);
    this.faceapi.draw.drawDetections(canvas, this.detections);
    this.faceapi.draw.drawFaceLandmarks(canvas, this.detections);
    this.faceapi.draw.drawFaceExpressions(canvas, this.detections);
  }
  alarm(critical) {
    if (!this.options.current.sound) return;
    this.audio ??= new AudioContext();
    const start = this.audio.currentTime;
    (critical ? [880, 660, 880, 660, 880] : [520, 440]).forEach((freq, i) => {
      const oscillator = this.audio.createOscillator(), gain = this.audio.createGain();
      oscillator.connect(gain); gain.connect(this.audio.destination);
      oscillator.frequency.value = freq;
      gain.gain.setValueAtTime(.15, start + i * .3);
      gain.gain.linearRampToValueAtTime(0, start + i * .3 + .25);
      oscillator.start(start + i * .3); oscillator.stop(start + i * .3 + .25);
    });
  }
  async dispose() { await this.audio?.close(); this.detections = []; }
}

import test from 'node:test';
import assert from 'node:assert/strict';
import { Camera } from '../frontend/src/core/camera.js';
import { Pipeline } from '../frontend/src/core/pipeline.js';
import { validateConfig } from '../frontend/src/core/config.js';
import { gesture, Stroke } from '../frontend/src/modules/air-logic.js';
import { ExamRules } from '../frontend/src/modules/exam-rules.js';

test('configuration rejects invalid acquisition and confidence settings', () => {
  assert.equal(validateConfig({}).width, 640);
  for (const config of [{ fps: 0 }, { width: -1 }, { height: 1 }, { confidence: NaN }, { confidence: 2 }]) assert.throws(() => validateConfig(config));
});
test('late camera permission cannot leak stream after stop', async () => {
  let resolve, stopped = 0;
  const video = { play: async () => {}, srcObject: null };
  const camera = new Camera(video, { getUserMedia: () => new Promise(r => { resolve = r; }) });
  const pending = camera.start(validateConfig({}));
  camera.stop();
  resolve({ getTracks: () => [{ stop: () => stopped++ }] });
  assert.equal(await pending, false); assert.equal(stopped, 1); assert.equal(video.srcObject, null);
});
test('camera releases stream when video playback fails', async () => {
  let stopped = 0;
  const camera = new Camera({ play: async () => { throw Error('play'); } }, { getUserMedia: async () => ({ getTracks: () => [{ stop: () => stopped++ }] }) });
  await assert.rejects(camera.start(validateConfig({})), /play/); assert.equal(stopped, 1);
});
function fixture() {
  let scheduled, results = [], cleared = 0;
  const context = { clearRect: () => cleared++, setTransform() {}, drawImage() {} };
  const canvas = () => ({ width: 640, height: 480, getContext: () => context });
  const pipeline = new Pipeline({ camera: { start: async () => true, stop() {} }, video: { readyState: 4, videoWidth: 640, videoHeight: 480 }, frame: canvas(), overlay: canvas(), onResult: value => results.push(value), onError: () => {}, schedule: callback => { scheduled = callback; return 1; }, cancel: () => { scheduled = null; } });
  return { pipeline, results, scheduled: () => scheduled, cleared: () => cleared };
}
test('stop waits for inference, suppresses stale results, disposes exactly once', async () => {
  const f = fixture(); let finish, disposed = 0;
  await f.pipeline.start({ id: 'fake', initialize: async () => {}, process: () => new Promise(r => { finish = r; }), dispose: async () => disposed++ }, validateConfig({}));
  f.scheduled()(100);
  const stopped = f.pipeline.stop();
  assert.equal(disposed, 0);
  finish({ old: true }); await stopped;
  assert.equal(disposed, 1); assert.equal(f.results.length, 0); assert.equal(f.scheduled(), null);
});
test('partial initialization releases module resources', async () => {
  const f = fixture(); let disposed = 0;
  await assert.rejects(f.pipeline.start({ initialize: async () => { throw Error('model missing'); }, dispose: async () => disposed++ }, validateConfig({})), /model missing/);
  assert.equal(disposed, 1); assert.equal(f.pipeline.module, null);
});
test('restart waits for an already-running asynchronous disposal', async () => {
  const f = fixture(); let release, initialized = false;
  await f.pipeline.start({ id: 'old', initialize: async () => {}, dispose: () => new Promise(resolve => { release = resolve; }) }, validateConfig({}));
  const stopping = f.pipeline.stop();
  await Promise.resolve(); await Promise.resolve();
  const starting = f.pipeline.start({ id: 'new', initialize: async () => { initialized = true; } }, validateConfig({}));
  await Promise.resolve(); await Promise.resolve();
  assert.equal(initialized, false);
  release(); await stopping; await starting;
  assert.equal(initialized, true);
  await f.pipeline.stop();
});
test('switching through three modules never renders old state', async () => {
  const f = fixture(), events = [];
  for (const id of ['vision_xe', 'air_write', 'sign_language', 'vision_xe']) {
    await f.pipeline.start({ id, initialize: async () => events.push(`start ${id}`), process: async () => ({ ok: true }), dispose: async () => events.push(`stop ${id}`) }, validateConfig({}));
    f.scheduled()(100); await f.pipeline.pending;
  }
  await f.pipeline.stop();
  assert.equal(f.results.length, 4);
  assert.deepEqual(events, ['start vision_xe', 'stop vision_xe', 'start air_write', 'stop air_write', 'start sign_language', 'stop sign_language', 'start vision_xe', 'stop vision_xe']);
});
test('gesture thresholds preserve index drawing, two-finger eraser and pinch priority', () => {
  const points = Array.from({ length: 21 }, () => ({ x: .5, y: .6 }));
  points[8] = { x: .5, y: .2 }; points[4] = { x: .1, y: .5 };
  assert.equal(gesture(points), 'draw');
  points[12].y = .2; assert.equal(gesture(points), 'erase');
  points[4] = { ...points[8] }; assert.equal(gesture(points, true), 'pause');
  assert.equal(gesture(null), 'no-hand');
});
test('stroke smoothing and pen-up avoid connecting unrelated strokes', () => {
  const stroke = new Stroke();
  assert.equal(stroke.update([0, 0], 'draw'), null);
  assert.deepEqual(stroke.update([100, 100], 'draw'), [[0, 0], [55.00000000000001, 55.00000000000001]]);
  stroke.update([200, 200], 'pause'); assert.equal(stroke.update([250, 250], 'draw'), null);
  stroke.update(null, 'no-hand'); assert.equal(stroke.point, null);
  stroke.update([100, 100], 'erase'); assert.equal(stroke.update([200, 200], 'draw'), null);
});
test('exam absence, cooldown and three-warning termination', () => {
  const rules = new ExamRules();
  assert.equal(rules.evaluate([], 0).warnings.length, 0);
  assert.equal(rules.evaluate([], 3000).warnings.length, 0);
  assert.equal(rules.evaluate([], 3001).warnings.length, 1);
  const faces = [{ expressions: {} }, { expressions: {} }];
  assert.equal(rules.evaluate(faces, 4000).warnings.length, 1);
  assert.equal(rules.evaluate(faces, 8002).warnings.length, 2);
  assert.equal(rules.evaluate(faces, 13003).terminated, true);
  assert.equal(rules.evaluate(faces, 19000).warnings.length, 3);
});
test('exam head and expression rules preserved', () => {
  const rules = new ExamRules();
  assert.equal(rules.evaluate([{ offset: .36, expressions: {} }], 0).warnings[0].reason, 'LOOKING AWAY');
  assert.match(rules.evaluate([{ offset: 0, expressions: { sad: .5 } }], 6000).warnings[1].reason, /SAD/);
});

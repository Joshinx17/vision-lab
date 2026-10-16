import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
const root = new URL('../', import.meta.url);
test('all face manifests have complete nonempty weight shards', () => {
  for (const name of ['tiny_face_detector', 'face_landmark_68', 'face_expression']) {
    const folder = new URL(`frontend/public/models/${name}/`, root);
    const manifest = JSON.parse(readFileSync(new URL(`${name}_model-weights_manifest.json`, folder)));
    for (const group of manifest) {
      let bytes = 0;
      for (const path of group.paths) bytes += readFileSync(new URL(path, folder)).length;
      const expected = group.weights.reduce((sum, weight) => sum + weight.shape.reduce((a, b) => a * b, 1) * (weight.quantization?.dtype === 'uint8' ? 1 : 4), 0);
      assert.equal(bytes, expected, `${name}: weight size`);
    }
  }
});
test('preserved source files match recorded audit baseline when present', () => {
  const baseline = JSON.parse(readFileSync(new URL('docs/source-baseline.json', root), 'utf8').replace(/^\uFEFF/, ''));
  for (const item of baseline) {
    const path = new URL(join(item.project, item.file).replaceAll('\\', '/'), root);
    if (!existsSync(path)) continue; // Original repositories are not needed in a clean checkout.
    assert.equal(createHash('sha256').update(readFileSync(path)).digest('hex').toUpperCase(), item.sha256, item.file);
  }
});

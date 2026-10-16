import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { resolve, relative, isAbsolute } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../', import.meta.url));
process.chdir(root);
if (existsSync('.env')) for (const line of readFileSync('.env', 'utf8').split(/\r?\n/)) {
  const match = line.trim().match(/^(VISION_[A-Z_]+)=(.*)$/);
  if (match) process.env[match[1]] ??= match[2].trim().replace(/^["']|["']$/g, '');
}
if (!existsSync('frontend/dist/index.html')) {
  console.error('Frontend missing. Run npm --prefix frontend ci, then npm run build.'); process.exit(1);
}
const localPython = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python';
let python = process.env.VISION_PYTHON || (existsSync(localPython) ? localPython : 'python');
if (python !== 'python') {
  python = resolve(root, python);
  const path = relative(root, python);
  if (path.startsWith('..') || isAbsolute(path)) throw new Error('VISION_PYTHON must be inside Vision-Lab.');
}
const child = spawn(python, ['-B', '-m', 'backend.server'], { cwd: root, stdio: 'inherit', windowsHide: true, env: { ...process.env, PYTHONUNBUFFERED: '1', MPLCONFIGDIR: resolve(root, '.cache/matplotlib'), KERAS_HOME: resolve(root, '.cache/keras') } });
child.on('error', error => { console.error(`Unable to launch Python: ${error.message}`); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 0; });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));

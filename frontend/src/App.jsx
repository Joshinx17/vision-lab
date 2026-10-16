import React, { useEffect, useRef, useState } from 'react';
import { Camera } from './core/camera.js';
import { Pipeline } from './core/pipeline.js';
import { defaults, validateConfig } from './core/config.js';
import { api } from './core/api.js';
import { modules } from './modules/registry.js';
import { COLORS, paint, erase } from './modules/air-logic.js';

const EMOTIONS = ['neutral', 'happy', 'sad', 'angry', 'fearful', 'disgusted', 'surprised'];

function History({ history, keys = EMOTIONS }) {
  return <svg viewBox="0 0 480 120" role="img" aria-label="Recent inference history" className="chart">
    {[0, .5, 1].map(v => <line key={v} x1="0" x2="480" y1={110 - v * 100} y2={110 - v * 100} stroke="#253746" />)}
    {keys.map((key, index) => <path key={key} fill="none" stroke={COLORS[index % COLORS.length]} strokeWidth="2" d={history.map((row, i) => `${i ? 'L' : 'M'} ${i * 480 / Math.max(1, history.length - 1)} ${110 - (row[key] || 0) * 100}`).join(' ')} />)}
  </svg>;
}

function SignTools({ frame, cameraOnly, stop, runAction, setResult, threshold }) {
  const [status, setStatus] = useState(null);
  const [letter, setLetter] = useState('A');
  const [epochs, setEpochs] = useState(20);
  const [batch, setBatch] = useState(32);
  const [rate, setRate] = useState(.001);
  const [preview, setPreview] = useState(null);
  const previewCanvas = useRef(null), cropCanvas = useRef(null);
  useEffect(() => {
    if (!preview) return;
    let active = true;
    const image = new Image();
    image.onload = () => {
      if (!active) return;
      const canvas = previewCanvas.current, crop = cropCanvas.current;
      canvas.width = image.width; canvas.height = image.height;
      const ctx = canvas.getContext('2d'); ctx.drawImage(image, 0, 0);
      const [x, y, right, bottom] = preview.result.bbox ?? [0, 0, image.width, image.height];
      crop.width = 160; crop.height = 160;
      crop.getContext('2d').drawImage(image, x, y, right - x, bottom - y, 0, 0, 160, 160);
      ctx.strokeStyle = '#63f2be'; ctx.lineWidth = 3;
      if (preview.result.bbox) ctx.strokeRect(x, y, right - x, bottom - y);
      for (const point of preview.result.landmarks ?? []) { ctx.beginPath(); ctx.arc(point[0] * image.width, point[1] * image.height, 3, 0, 2 * Math.PI); ctx.stroke(); }
    };
    image.src = preview.image;
    return () => { active = false; };
  }, [preview]);
  useEffect(() => {
    let active = true;
    const refresh = () => api('status').then(value => { if (active) setStatus(value); }).catch(() => {});
    refresh(); const timer = setInterval(refresh, 2000);
    return () => { active = false; clearInterval(timer); };
  }, []);
  const snapshot = () => {
    if (!frame.current?.width || frame.current.width <= 1) throw new Error('Start the camera before capturing a sample.');
    return frame.current.toDataURL('image/png');
  };
  const upload = event => {
    const file = event.target.files?.[0]; event.target.value = '';
    if (!file) return;
    runAction(async () => {
      await stop();
      if (!['image/jpeg', 'image/png'].includes(file.type) || file.size > 3_000_000) throw new Error('Choose a JPEG or PNG under 3 MB.');
      const image = await new Promise((resolve, reject) => {
        const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file);
      });
      try {
        const result = await api('sign/predict', { image, threshold });
        setPreview({ image, result });
        setResult({ ...result, module: 'sign_language', timestamp: Date.now() });
      } finally { await api('sign/close', {}); }
    });
  };
  return <section className="panel tools">
    <h2>Sign language workbench</h2>
    <p>{status?.model_exists ? 'Model file found · validated when inference starts' : 'No trained model supplied. Capture samples or provide your existing model.'}</p>
    <label className="file">Predict an image<input type="file" accept="image/jpeg,image/png" onChange={upload} /></label>
    {preview && <div><h3>Image prediction</h3><canvas ref={previewCanvas} style={{ width: '100%' }} /><p>{preview.result.fallback ? 'Full image fallback' : 'Hand crop'} · displayed at 160px; CNN input remains 64×64 BGR.</p><canvas ref={cropCanvas} /></div>}
    <details><summary>Capture a dataset</summary>
      <p>Saved frames contain mirrored camera pixels only, without overlays.</p>
      <button onClick={() => runAction(cameraOnly)}>Start capture camera</button>
      <label>Letter<select value={letter} onChange={e => setLetter(e.target.value)}>{Array.from({ length: 26 }, (_, i) => String.fromCharCode(65 + i)).map(l => <option key={l}>{l}</option>)}</select></label>
      <button onClick={() => runAction(async () => { await api('dataset/capture', { letter, image: snapshot() }); setStatus(await api('status')); })}>Save sample</button>
      <div className="dataset">{Object.entries(status?.dataset ?? {}).map(([key, count]) => <span key={key}>{key} <b>{count}</b></span>)}</div>
      <img className="reference" src="/asl_reference.png" alt="Original ASL alphabet reference chart" />
    </details>
    <details><summary>Train the original CNN</summary>
      <p>Requires at least five valid images per letter. Existing model files are never overwritten. Validation accuracy is not a guarantee of real-world recognition.</p>
      <label>Epochs<input type="number" min="1" max="100" value={epochs} onChange={e => setEpochs(Number(e.target.value))} /></label>
      <label>Batch size<select value={batch} onChange={e => setBatch(Number(e.target.value))}>{[16, 32, 64, 128].map(v => <option key={v}>{v}</option>)}</select></label>
      <label>Learning rate<select value={rate} onChange={e => setRate(Number(e.target.value))}>{[.0001, .001, .01].map(v => <option key={v}>{v}</option>)}</select></label>
      <button disabled={status?.training.state === 'running' || status?.model_exists} onClick={() => runAction(async () => { await stop(); await api('train', { epochs, batch_size: batch, learning_rate: rate }); setStatus(await api('status')); })}>Train new model</button>
      <p aria-live="polite">Training: {status?.training.state ?? 'unknown'} {status?.training.epoch ? `· epoch ${status.training.epoch}/${status.training.epochs}` : ''}</p>
      {status?.training.error && <p role="alert">{status.training.error}</p>}
      <History history={status?.training.history ?? []} keys={['accuracy', 'val_accuracy']} />
      <small>Cyan: training accuracy · magenta: validation accuracy</small>
      <History history={status?.training.history ?? []} keys={['loss', 'val_loss']} />
      <small>Cyan: training loss · magenta: validation loss (chart range 0–1)</small>
      {status?.training.accuracy !== undefined && <p>Held-out accuracy: {(status.training.accuracy * 100).toFixed(1)}% · loss {status.training.loss.toFixed(3)}</p>}
    </details>
  </section>;
}

export default function App() {
  const video = useRef(null), overlay = useRef(null), frame = useRef(null), pipeline = useRef(null), pointer = useRef(null);
  const options = useRef({ color: COLORS[0], size: 8, eraser: false, exam: false, sound: false });
  const [selected, setSelected] = useState(modules[0]);
  const [config, setConfig] = useState(defaults);
  const [devices, setDevices] = useState([]);
  const [busy, setBusy] = useState(false), [running, setRunning] = useState(false), [pointerMode, setPointerMode] = useState(false);
  const [phase, setPhase] = useState('');
  const [error, setError] = useState(''), [result, setResult] = useState(null), [history, setHistory] = useState([]);
  const [settings, setSettings] = useState(options.current), [grid, setGrid] = useState(false);
  const change = patch => { options.current = { ...options.current, ...patch }; setSettings(options.current); };
  useEffect(() => {
    frame.current = document.createElement('canvas'); frame.current.width = 1;
    const camera = new Camera(video.current);
    pipeline.current = new Pipeline({ camera, video: video.current, frame: frame.current, overlay: overlay.current,
      onStatus: setPhase,
      onResult: data => {
        setResult(data);
        if (data.expressions) setHistory(rows => [...rows.slice(-39), data.expressions]);
        if (data.terminated) setRunning(false);
      },
      onError: err => { console.error('Frame processing failed', err); setError(err.message); setRunning(false); },
    });
    const release = () => camera.stop();
    window.addEventListener('pagehide', release);
    return () => { window.removeEventListener('pagehide', release); void pipeline.current.stop(); };
  }, []);
  const stop = async () => {
    setRunning(false); setPointerMode(false); pointer.current = null;
    await pipeline.current.stop();
    frame.current.width = 1;
  };
  const runAction = async action => {
    if (busy) return;
    setBusy(true); setError('');
    try { await action(); }
    catch (err) { console.error('Vision-Lab action failed', err); setError(err.message || 'Operation failed. See logs.'); }
    finally { setBusy(false); }
  };
  const start = async () => {
    await stop(); setResult(null); setHistory([]);
    await pipeline.current.start(selected.create(options), validateConfig(config)); setRunning(true);
    setDevices((await navigator.mediaDevices.enumerateDevices()).filter(device => device.kind === 'videoinput'));
  };
  const cameraOnly = async () => {
    await stop();
    await pipeline.current.start({ id: 'dataset_capture', initialize: async () => {}, process: async () => ({ capturing: true }) }, validateConfig(config));
    setRunning(true);
  };
  const clear = () => {
    const canvas = overlay.current; canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
    pipeline.current.module?.clear?.(); pointer.current = null;
  };
  useEffect(() => {
    if (selected.id !== 'air_write') return;
    const keydown = event => {
      if (/INPUT|SELECT|TEXTAREA/.test(event.target.tagName)) return;
      const key = event.key.toLowerCase();
      if (key === 'c') clear();
      if (key === 'e') change({ eraser: !options.current.eraser });
      if (key === 'g') setGrid(value => !value);
      const index = Number(key) - 1;
      if (COLORS[index]) change({ color: COLORS[index], eraser: false });
    };
    window.addEventListener('keydown', keydown);
    return () => window.removeEventListener('keydown', keydown);
  }, [selected]);
  const point = event => {
    const canvas = overlay.current, rect = canvas.getBoundingClientRect();
    return [(event.clientX - rect.left) * canvas.width / rect.width, (event.clientY - rect.top) * canvas.height / rect.height];
  };
  return <div className="app">
    <aside><div className="brand">◈ <span>VISION<em>LAB</em></span></div><p className="eyebrow">COMPUTER VISION WORKSPACE</p>
      <nav aria-label="Modules">{modules.map((module, i) => <button disabled={busy} className={selected.id === module.id ? 'selected' : ''} key={module.id} onClick={() => runAction(async () => { await stop(); setSelected(module); setResult(null); setHistory([]); })}><span className="number">0{i + 1}</span><span>{module.name}<small>{module.subtitle}</small></span></button>)}</nav>
      <div className="privacy"><span className="dot" /> LOCAL PROCESSING<p>Camera starts only when requested. Sign frames go to the service on this computer.</p></div>
    </aside>
    <main><header><div><p className="eyebrow">MODULAR REAL-TIME VISION</p><h1>{selected.name}</h1><p>{selected.subtitle}</p></div><span className={`status ${running ? 'live' : ''}`}>{busy ? phase || 'Working…' : running ? '● Camera active' : pointerMode ? 'Pointer mode' : 'Ready'}</span></header>
      <fieldset disabled={busy} className="workspace">
        <div className="primary"><div className="toolbar"><button className="primary-button" disabled={running} onClick={() => runAction(start)}>Start camera</button><button disabled={!running && !pointerMode && !result} onClick={() => runAction(stop)}>Stop</button>
          {selected.id === 'air_write' && <button onClick={() => runAction(async () => { await stop(); overlay.current.width = 640; overlay.current.height = 480; setPointerMode(true); setResult(null); })}>Mouse / touch</button>}
        </div>
        {error && <div className="error" role="alert">{error}<button onClick={() => setError('')}>Dismiss</button></div>}
        <div className={`stage ${grid && selected.id === 'air_write' ? 'grid' : ''}`}>
          <video ref={video} autoPlay playsInline muted style={{ visibility: running ? 'visible' : 'hidden' }} />
          <canvas ref={overlay} width="640" height="480" onPointerDown={event => { if (pointerMode) { event.currentTarget.setPointerCapture(event.pointerId); pointer.current = point(event); } }} onPointerMove={event => {
            if (!pointerMode || !pointer.current) return;
            const next = point(event), ctx = overlay.current.getContext('2d');
            if (settings.eraser) erase(ctx, next, settings.size); else paint(ctx, [pointer.current, next], settings.color, settings.size);
            pointer.current = next;
          }} onPointerUp={() => { pointer.current = null; }} onPointerCancel={() => { pointer.current = null; }} />
          {!running && !pointerMode && <div className="placeholder"><span>◎</span><p>{result?.terminated ? 'Demonstration session ended · start again to reset' : 'Your vision workspace'}<small>Choose your settings, then start the camera.</small></p></div>}
          {selected.id === 'air_write' && result?.coordinates && running && <div className="cursor" style={{ left: `${result.coordinates[0] / overlay.current.width * 100}%`, top: `${result.coordinates[1] / overlay.current.height * 100}%`, borderColor: settings.color }} />}
        </div>
        <div className="metrics"><span><b>{result?.fps?.toFixed(1) ?? '—'}</b> processed FPS</span><span><b>{result?.processing_ms?.toFixed(0) ?? '—'}</b> ms / frame</span><span><b>{result?.inference_ms?.toFixed(0) ?? '—'}</b> ms sign inference</span></div>
        {selected.id === 'air_write' && <section className="panel"><h2>Drawing tools</h2><p>Index finger: draw · two fingers: erase · pinch: pause</p><div className="swatches">{COLORS.map((color, index) => <button key={color} aria-label={`Color ${index + 1}`} aria-pressed={settings.color === color} style={{ background: color }} onClick={() => change({ color, eraser: false })} />)}</div><label>Brush {settings.size}px<input type="range" min="2" max="30" value={settings.size} onChange={e => change({ size: Number(e.target.value) })} /></label><button aria-pressed={settings.eraser} onClick={() => change({ eraser: !settings.eraser })}>Eraser (E)</button><button onClick={clear}>Clear (C)</button><button aria-pressed={grid} onClick={() => setGrid(!grid)}>Grid (G)</button><p>{result?.gesture ?? 'Awaiting input'} · keys 1–7 change color</p></section>}
        {selected.id === 'vision_xe' && <section className="panel"><h2>Live analytics <span>{result?.dominant ?? 'No face'}</span></h2>{EMOTIONS.map((emotion, index) => <div className="expression" key={emotion}><span style={{ color: COLORS[index] }}>{emotion}</span><progress max="1" value={result?.expressions?.[emotion] ?? 0} /><b>{((result?.expressions?.[emotion] ?? 0) * 100).toFixed(1)}%</b></div>)}<History history={history} /><small>Last 40 processed samples. Expression scores are model outputs, not evidence of a person's intent.</small><label><input type="checkbox" checked={settings.exam} onChange={e => change({ exam: e.target.checked })} /> Examination demonstration</label><label><input type="checkbox" checked={settings.sound} onChange={e => change({ sound: e.target.checked })} /> Warning sounds</label>{settings.exam && <p>Original rules: absence over 3s, multiple faces, head offset &gt;0.35, selected expression scores &gt;0.4. Three warnings end this demo; 5s cooldown. Not suitable for judging cheating.</p>}{result?.warnings?.map((warning, index) => <p className="warning" key={warning.timestamp}>Warning {index + 1}/3 · {warning.reason}</p>)}</section>}
        {selected.id === 'sign_language' && <SignTools frame={frame} cameraOnly={cameraOnly} stop={stop} runAction={runAction} setResult={setResult} threshold={config.confidence} />}
        </div>
        <div className="secondary"><section className="panel"><h2>Session settings</h2><label>Camera<select disabled={running} value={config.deviceId} onChange={e => setConfig({ ...config, deviceId: e.target.value })}><option value="">Default camera</option>{devices.map((device, index) => <option key={device.deviceId} value={device.deviceId}>{device.label || `Camera ${index + 1}`}</option>)}</select></label><label>Resolution<select disabled={running} value={`${config.width}x${config.height}`} onChange={e => { const [width, height] = e.target.value.split('x').map(Number); setConfig({ ...config, width, height }); }}><option>640x480</option><option>1280x720</option><option>1920x1080</option></select></label><label>Target FPS<input disabled={running} type="number" min="1" max="60" value={config.fps} onChange={e => setConfig({ ...config, fps: Number(e.target.value) })} /></label><label>Sign confidence threshold<input disabled={running} type="number" min="0" max="1" step=".05" value={config.confidence} onChange={e => setConfig({ ...config, confidence: Number(e.target.value) })} /></label><small>Actual throughput depends on inference time. Changes apply on next start.</small></section>
        <section className="panel"><h2>Latest result</h2>{result?.label && <div className="prediction"><b>{result.label}</b><span>{(result.confidence * 100).toFixed(1)}% confidence</span>{!result.accepted && <p>Below confidence threshold</p>}{result.fallback && <p className="warning">No hand crop: classifying the full frame.</p>}</div>}<pre>{result ? JSON.stringify(result, (key, value) => ['segment', 'landmarks', 'detections'].includes(key) ? undefined : value, 2) : 'No frames processed yet.'}</pre></section>
        </div>
      </fieldset><footer>VISION-LAB / LOCAL WORKSPACE <span>One camera · three capabilities</span></footer>
    </main>
  </div>;
}

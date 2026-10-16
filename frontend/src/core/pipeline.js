// One inference in flight; teardown waits before disposing native/WASM resources.
export class Pipeline {
  constructor({ camera, video, frame, overlay, onResult, onError, onStatus = () => {}, schedule = callback => requestAnimationFrame(callback), cancel = handle => cancelAnimationFrame(handle) }) {
    Object.assign(this, { camera, video, frame, overlay, onResult, onError, onStatus, schedule, cancel });
    this.generation = 0;
    this.pending = Promise.resolve();
    this.module = null;
    this.handle = null;
  }
  async start(module, config) {
    await this.stop();
    const generation = this.generation;
    this.module = module;
    this.config = config;
    this.pending = (async () => {
      this.onStatus('Loading module…');
      console.info('Initializing module', module.id);
      await module.initialize({ config, canvas: this.overlay });
      if (generation !== this.generation) return;
      this.onStatus('Waiting for camera…');
      if (!await this.camera.start(config)) return;
      if (generation === this.generation) this.queue(generation);
      this.onStatus('');
    })();
    try { await this.pending; }
    catch (error) { await this.stop(); throw error; }
  }
  queue(generation) {
    this.handle = this.schedule(time => {
      this.pending = this.tick(time, generation);
      this.pending.catch(error => {
        if (generation !== this.generation) return;
        this.onError(error);
        void this.stop();
      });
    });
  }
  async tick(time, generation) {
    if (generation !== this.generation) return;
    if (this.video.readyState < 2 || (this.lastTime !== undefined && time - this.lastTime < 1000 / this.config.fps)) {
      this.queue(generation); return;
    }
    const previous = this.lastTime;
    this.lastTime = time;
    const width = this.video.videoWidth, height = this.video.videoHeight;
    if (this.frame.width !== width || this.frame.height !== height) {
      this.frame.width = this.overlay.width = width;
      this.frame.height = this.overlay.height = height;
    }
    // All processors see the same mirrored pixels; overlay is never CSS-flipped.
    const ctx = this.frame.getContext('2d');
    ctx.setTransform(-1, 0, 0, 1, width);
    ctx.drawImage(this.video, 0, 0, width, height);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const start = performance.now();
    const result = await this.module.process(this.frame);
    if (generation !== this.generation) return;
    this.module.render?.(result, this.overlay);
    this.onResult({ ...result, module: this.module.id, timestamp: Date.now(), processing_ms: performance.now() - start, fps: previous === undefined ? 0 : 1000 / (time - previous) });
    if (result.terminated) { this.camera.stop(); return; }
    this.queue(generation);
  }
  async stop() {
    this.generation++;
    this.cancel(this.handle);
    this.camera.stop();
    if (!this.teardown) {
      this.teardown = (async () => {
        await this.pending.catch(() => {});
        const module = this.module;
        this.module = null;
        try { await module?.dispose?.(); }
        finally {
          if (module) console.info('Disposed module', module.id);
          this.onStatus('');
          this.lastTime = undefined;
          this.overlay.getContext('2d').clearRect(0, 0, this.overlay.width, this.overlay.height);
        }
      })();
    }
    const teardown = this.teardown;
    try { await teardown; }
    finally { if (this.teardown === teardown) this.teardown = null; }
  }
}

export class Camera {
  constructor(video, mediaDevices = navigator.mediaDevices) {
    this.video = video;
    this.mediaDevices = mediaDevices;
    this.stream = null;
    this.generation = 0;
  }
  async start(config) {
    this.stop();
    const generation = this.generation;
    if (!this.mediaDevices?.getUserMedia) throw new Error('Camera requires localhost or HTTPS and a supported browser.');
    let timer;
    const request = this.mediaDevices.getUserMedia({ audio: false, video: {
      width: { ideal: config.width }, height: { ideal: config.height },
      frameRate: { ideal: config.fps },
      ...(config.deviceId ? { deviceId: { exact: config.deviceId } } : { facingMode: 'user' }),
    } }).then(stream => {
      if (generation !== this.generation) { stream.getTracks().forEach(t => t.stop()); return null; }
      return stream;
    });
    let stream;
    try {
      stream = await Promise.race([request, new Promise((_, reject) => {
        timer = setTimeout(() => reject(new Error('Camera permission timed out. Allow camera access or open Vision-Lab in Chrome/Edge.')), 15000);
      })]);
    } catch (error) { this.stop(); throw error; }
    finally { clearTimeout(timer); }
    if (!stream) return false;
    if (generation !== this.generation) { stream.getTracks().forEach(t => t.stop()); return false; }
    this.stream = stream;
    this.video.srcObject = stream;
    try { await this.video.play(); }
    catch (error) { this.stop(); throw error; }
    return generation === this.generation;
  }
  stop() {
    this.generation++;
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = null;
    this.video.srcObject = null;
  }
}

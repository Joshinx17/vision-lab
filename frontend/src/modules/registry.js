import { AirWrite } from './air.js';
import { VisionXE } from './vision.js';
import { SignLanguage } from './sign.js';
export const modules = [
  { id: 'vision_xe', name: 'Vision-XE', subtitle: 'Faces, expressions & session analytics', create: options => new VisionXE(options) },
  { id: 'air_write', name: 'Air Write', subtitle: 'Draw and erase with hand gestures', create: options => new AirWrite(options) },
  { id: 'sign_language', name: 'Sign Language', subtitle: 'A–Z image classification & dataset tools', create: () => new SignLanguage() },
];

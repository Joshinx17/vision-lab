import { api } from './api.js';

export async function moduleResources(id) {
  const report = await api('resources');
  if (report.error) throw new Error(report.error);
  const entry = report.modules[id];
  if (!entry?.ready) throw new Error(entry?.issues?.join(' ') || 'Module resources unavailable. Check the Models & resources panel.');
  return entry.config;
}

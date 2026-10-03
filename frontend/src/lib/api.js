// Thin client for the VisionGuard FastAPI backend (proxied by Vite in dev).

async function request(path, { method = 'GET', body, form } = {}) {
  const opts = { method, headers: {} };
  if (form) opts.body = form;
  else if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  let data = null;
  try { data = await res.json(); } catch { /* empty or non-JSON body */ }
  if (!res.ok) {
    const detail = data?.detail || data?.message || `${res.status} ${res.statusText}`;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}

export const api = {
  login: (username, password) => request('/api/login', { method: 'POST', body: { username, password } }),
  cameras: () => request('/api/cameras'),
  status: () => request('/api/status'),
  evidence: () => request('/api/evidence'),
  voice: (text) => request('/api/voice', { method: 'POST', body: { text } }),
  connectCamera: (cam) => request('/api/cameras/connect', { method: 'POST', body: cam }),
  disconnectCamera: (id) => request(`/api/cameras/disconnect/${encodeURIComponent(id)}`, { method: 'POST' }),
  testConnection: (type, source) => request('/api/cameras/test-connection', { method: 'POST', body: { type, source: String(source) } }),
  uploadVideo: (file) => {
    const form = new FormData();
    form.append('file', file);
    return request('/api/cameras/upload-test-video', { method: 'POST', form });
  },
};

export const feedUrl = (id) => `/video_feed/${encodeURIComponent(id)}`;
export const evidenceUrl = (name) => `/evidence_files/${encodeURIComponent(name)}`;

export function wsUrl(path) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.host}${path}`;
}

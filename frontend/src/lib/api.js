// Client for the VisionGuard FastAPI backend (prototype/web/server.py).
// In dev, Vite proxies /api, /ws, /video_feed and /evidence_files to :8000.
// Every call carries the operator's session token; a 401 signs the console out.

const TOKEN_KEY = 'vg.token';
let token = (() => { try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } })();
let onUnauthorized = () => {};

export const session = {
  get token() { return token; },
  set(t) { token = t || ''; try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ } },
  onUnauthorized(fn) { onUnauthorized = fn; },
};

async function request(path, options = {}) {
  const headers = {};
  if (!(options.body instanceof FormData)) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...options, headers: { ...headers, ...options.headers } });
  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }
  if (res.status === 401 && path !== '/api/login') onUnauthorized();
  if (!res.ok) {
    const detail = data?.detail || data?.message || `Request failed (${res.status})`;
    const err = new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
    err.status = res.status;
    throw err;
  }
  return data;
}

const send = (method, path, body) => request(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
const enc = encodeURIComponent;

export const api = {
  // auth & profile
  login: (username, password, station) => send('POST', '/api/login', { username, password, station }),
  logout: () => send('POST', '/api/logout'),
  me: () => request('/api/me'),
  changePassword: (current, next) => send('POST', '/api/me/password', { current, new: next }),
  savePreferences: (prefs) => send('PUT', '/api/me/preferences', prefs),

  // system
  status: () => request('/api/status'),
  telemetry: () => request('/api/telemetry/specialists'),

  // cameras
  cameras: () => request('/api/cameras'),
  camera: (id) => request(`/api/cameras/${enc(id)}`),
  connectCamera: (payload) => send('POST', '/api/cameras/connect', payload),
  updateCamera: (id, payload) => send('PUT', `/api/cameras/${enc(id)}`, payload),
  startCamera: (id) => send('POST', `/api/cameras/${enc(id)}/start`),
  stopCamera: (id) => send('POST', `/api/cameras/${enc(id)}/stop`),
  deleteCamera: (id) => send('DELETE', `/api/cameras/${enc(id)}`),
  testConnection: (type, source) => send('POST', '/api/cameras/test-connection', { type, source }),
  uploadVideo: (file) => {
    const fd = new FormData();
    fd.append('file', file);
    return request('/api/cameras/upload-test-video', { method: 'POST', body: fd });
  },

  // recorders & network cameras
  deviceBrands: () => request('/api/devices/brands'),
  devices: () => request('/api/devices'),
  discoverDevices: (subnet) => send('POST', '/api/devices/discover', subnet ? { subnet } : {}),
  probeDevice: (payload) => send('POST', '/api/devices/probe', payload),
  addDevice: (payload) => send('POST', '/api/devices/add', payload),
  deleteDevice: (id) => send('DELETE', `/api/devices/${enc(id)}`),

  // sample footage
  demoVideos: () => request('/api/demo-videos'),
  deployDemo: (videos) => send('POST', '/api/demo-videos/deploy', videos ? { videos } : {}),
  clearDemo: () => send('POST', '/api/demo-videos/clear'),

  // locations
  locations: () => request('/api/locations'),
  addCity: (name) => send('POST', '/api/locations/cities', { name }),
  addArea: (cityId, name) => send('POST', `/api/locations/cities/${enc(cityId)}/areas`, { name }),
  addStreet: (areaId, name) => send('POST', `/api/locations/areas/${enc(areaId)}/streets`, { name }),
  renameLocation: (level, id, name) => send('PUT', `/api/locations/${level}/${enc(id)}`, { name }),
  deleteLocation: (level, id) => send('DELETE', `/api/locations/${level}/${enc(id)}`),
  placeCamera: (id, p) => send('PUT', `/api/cameras/${enc(id)}/location`, p),
  unplaceCamera: (id) => send('DELETE', `/api/cameras/${enc(id)}/location`),

  // incidents & evidence
  incidents: (days = 7, status = '') => request(`/api/incidents?days=${days}&status=${enc(status)}`),
  incidentStats: (days = 30) => request(`/api/incidents/stats?days=${days}`),
  incidentAction: (code, action, note = '') => send('POST', `/api/incidents/${enc(code)}/action`, { action, note }),
  evidence: () => request('/api/evidence'),

  // voice
  voice: (text) => send('POST', '/api/voice', { text }),
  voiceLog: (limit = 50) => request(`/api/voice/log?limit=${limit}`),
  logVoice: (entry) => send('POST', '/api/voice/log', entry),

  // administration
  users: () => request('/api/users'),
  createUser: (u) => send('POST', '/api/users', u),
  updateUser: (username, u) => send('PUT', `/api/users/${enc(username)}`, u),
  resetPassword: (username, password) => send('POST', `/api/users/${enc(username)}/reset-password`, { password }),
  deleteUser: (username) => send('DELETE', `/api/users/${enc(username)}`),
  audit: (params = {}) => request(`/api/audit?${new URLSearchParams(params)}`),
};

const withToken = (url) => `${url}${url.includes('?') ? '&' : '?'}token=${enc(token)}`;
export const feedUrl = (id) => withToken(`/video_feed/${enc(id)}`);
export const mediaUrl = (path) => withToken(path);
export const evidenceUrl = (name) => withToken(`/evidence_files/${enc(name)}`);

export function wsUrl(path) {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return withToken(`${proto}://${window.location.host}${path}`);
}

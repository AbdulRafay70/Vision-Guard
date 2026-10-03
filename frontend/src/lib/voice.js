// Voice control: browser speech recognition + an intent parser that maps
// operator phrases onto console actions. Phrases the console cannot resolve
// locally are still sent to the backend interpreter (/ws/voice) which returns
// a structured command and a spoken response.
import { useCallback, useEffect, useRef, useState } from 'react';

const NUMBER_WORDS = {
  one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8,
  nine: 9, ten: 10, eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16,
  first: 1, second: 2, third: 3, fourth: 4, fifth: 5,
};

const PAGES = [
  { page: 'dashboard', words: ['dashboard', 'home', 'overview', 'operations'] },
  { page: 'live', words: ['live view', 'live', 'video wall', 'monitor'] },
  { page: 'registry', words: ['camera list', 'list of cameras', 'registry', 'directory', 'all cameras'] },
  { page: 'connect', words: ['connect camera', 'add camera', 'new camera', 'connection'] },
  { page: 'incidents', words: ['incidents', 'alerts', 'evidence', 'events'] },
  { page: 'analytics', words: ['analytics', 'statistics', 'reports', 'heat map', 'heatmap', 'trends'] },
  { page: 'health', words: ['system health', 'health', 'telemetry', 'diagnostics'] },
  { page: 'users', words: ['users', 'operators', 'accounts', 'user management'] },
  { page: 'audit', words: ['audit', 'audit log', 'activity log'] },
  { page: 'settings', words: ['settings', 'preferences', 'profile', 'my account'] },
];

// Wake phrases for hands-free mode
export const WAKE_WORDS = ['vision guard', 'visionguard', 'guard', 'command'];

export function stripWakeWord(text) {
  const t = text.trim().toLowerCase();
  for (const w of WAKE_WORDS) {
    if (t.startsWith(w)) return text.trim().slice(w.length).replace(/^[\s,.:]+/, '');
  }
  return null;
}

const norm = (s) => ` ${s.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim()} `;

function toNumber(token) {
  if (!token) return null;
  if (/^\d+$/.test(token)) return parseInt(token, 10);
  return NUMBER_WORDS[token] ?? null;
}

function findCamera(text, cameras) {
  // 1. Name match — prefer the longest camera name that appears in the phrase
  const byName = cameras
    .filter((c) => c.name && text.includes(norm(c.name)))
    .sort((a, b) => b.name.length - a.name.length)[0];
  if (byName) return byName;
  // 2. Id match
  const byId = cameras.find((c) => text.includes(norm(c.id.replace(/[_-]/g, ' '))) || text.includes(` ${c.id.toLowerCase()} `));
  if (byId) return byId;
  // 3. "camera 3" → third camera on the console
  const m = text.match(/ (?:camera|cam|feed|number) (\w+) /);
  const n = toNumber(m?.[1]);
  if (n && n >= 1 && n <= cameras.length) return cameras[n - 1];
  return null;
}

function findLocation(text, cities) {
  let best = null;
  const consider = (name, scope) => {
    if (name && text.includes(norm(name)) && (!best || name.length > best.len)) best = { scope, len: name.length, name };
  };
  for (const c of cities) {
    consider(c.name, { cityId: c.id });
    for (const a of c.areas) {
      consider(a.name, { cityId: c.id, areaId: a.id });
      for (const s of a.streets) consider(s.name, { cityId: c.id, areaId: a.id, streetId: s.id });
    }
  }
  return best;
}

/**
 * Parse an operator phrase into a console intent.
 * ctx: { cameras: [{id,name}], cities }
 */
export function parseIntent(raw, ctx) {
  const t = norm(raw);
  const has = (...w) => w.some((x) => t.includes(` ${x} `) || t.includes(` ${x}`));

  if (has('log out', 'logout', 'sign out')) return { type: 'logout', say: 'Signing out.' };
  if (has('full screen', 'fullscreen', 'maximize', 'maximise')) return { type: 'fullscreen', say: 'Full screen.' };
  if (has('exit full', 'restore')) return { type: 'exitFullscreen', say: 'Restoring view.' };
  if (has('zoom in')) return { type: 'zoom', dir: 1, say: 'Zooming in.' };
  if (has('zoom out')) return { type: 'zoom', dir: -1, say: 'Zooming out.' };
  if (has('reset zoom')) return { type: 'zoom', dir: 0, say: 'Zoom reset.' };

  const layout = t.match(/ (?:grid|layout|split)(?: of)? (\w+)(?: by (\w+))? /) || t.match(/ (\w+) by (\w+) /);
  if (layout) {
    const a = toNumber(layout[1]);
    const b = toNumber(layout[2]);
    const n = a && b ? a * b : a;
    const size = [1, 4, 9, 16].find((s) => s >= (n || 0));
    if (size) return { type: 'layout', size, say: `Layout set to ${Math.sqrt(size)} by ${Math.sqrt(size)}.` };
  }
  if (has('single view', 'single camera')) return { type: 'layout', size: 1, say: 'Single view.' };
  if (has('next page')) return { type: 'page', dir: 1, say: 'Next page.' };
  if (has('previous page', 'last page', 'page back')) return { type: 'page', dir: -1, say: 'Previous page.' };
  if (has('refresh', 'reload')) return { type: 'refresh', say: 'Refreshing.' };

  const cam = findCamera(t, ctx.cameras);
  if (cam && has('pin', 'add', 'put') && has('dashboard', 'wall')) return { type: 'pin', cameraId: cam.id, say: `${cam.name} added to dashboard.` };
  if (cam && has('remove', 'unpin', 'take off')) return { type: 'unpin', cameraId: cam.id, say: `${cam.name} removed from dashboard.` };
  if (cam && has('stop', 'turn off', 'disable', 'disconnect')) return { type: 'stopCamera', cameraId: cam.id, say: `Stopping ${cam.name}.` };
  if (cam && has('start', 'turn on', 'enable', 'reconnect', 'restart')) return { type: 'startCamera', cameraId: cam.id, say: `Starting ${cam.name}.` };
  if (cam) return { type: 'focus', cameraId: cam.id, say: `Showing ${cam.name}.` };

  if (has('clear filter', 'all locations', 'show all', 'every camera')) return { type: 'scope', scope: {}, say: 'Showing all cameras.' };
  const loc = findLocation(t, ctx.cities);
  if (loc) return { type: 'scope', scope: loc.scope, say: `Showing cameras in ${loc.name}.` };

  if (has('go to', 'open', 'show', 'switch to', 'navigate')) {
    for (const p of PAGES) if (p.words.some((w) => t.includes(` ${w} `))) return { type: 'navigate', page: p.page, say: `Opening ${p.words[0]}.` };
  }
  return null;
}

// Map a backend interpreter command onto a console intent where possible.
export function intentFromBackend(command, ctx) {
  if (!command) return null;
  const p = command.params || {};
  switch (command.action) {
    case 'switch_camera': {
      const key = String(p.camera_id || p.camera_name || '').toLowerCase();
      const cam = key && ctx.cameras.find((c) => c.id.toLowerCase() === key || c.name.toLowerCase().includes(key));
      return cam ? { type: 'focus', cameraId: cam.id } : null;
    }
    case 'show_cameras': {
      const loc = p.zone && findLocation(norm(String(p.zone)), ctx.cities);
      return loc ? { type: 'scope', scope: loc.scope } : null;
    }
    case 'zoom_in': return { type: 'zoom', dir: 1 };
    case 'zoom_out': return { type: 'zoom', dir: -1 };
    case 'show_heatmap': return { type: 'navigate', page: 'analytics' };
    case 'system_health': return { type: 'navigate', page: 'health' };
    case 'confirm_alert':
    case 'dismiss_alert': return { type: 'navigate', page: 'incidents' };
    default: return null;
  }
}

export function speak(text, lang = 'en-US') {
  if (!text || !('speechSynthesis' in window)) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    u.lang = lang;
    window.speechSynthesis.speak(u);
  } catch { /* speech output unavailable */ }
}

/**
 * Speech recognition. Push-to-talk by default; in hands-free mode it listens
 * continuously (restarting itself) and only acts on phrases that begin with a
 * wake word, e.g. "Guard, show camera 2".
 */
export function useSpeech(onFinal, { handsFree = false, lang = 'en-US' } = {}) {
  const Rec = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const [error, setError] = useState('');
  const recRef = useRef(null);
  const wantRef = useRef(false);
  const cb = useRef(onFinal);
  const modeRef = useRef(handsFree);
  useEffect(() => { cb.current = onFinal; }, [onFinal]);
  useEffect(() => { modeRef.current = handsFree; }, [handsFree]);

  const begin = useCallback(() => {
    if (!Rec || recRef.current) return;
    const rec = new Rec();
    rec.lang = lang;
    rec.interimResults = true;
    rec.continuous = modeRef.current;
    rec.onresult = (e) => {
      let text = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        text += e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          const said = text.trim();
          text = '';
          if (!modeRef.current) cb.current(said);
          else {
            const cmd = stripWakeWord(said);
            if (cmd) cb.current(cmd);
          }
        }
      }
      setInterim(text);
    };
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        wantRef.current = false;
        setError('Microphone permission was denied. Allow microphone access for this site.');
      } else if (e.error === 'network') {
        setError('Speech service unreachable. Check the internet connection.');
      }
    };
    rec.onend = () => {
      recRef.current = null;
      setInterim('');
      if (wantRef.current && modeRef.current) {
        setTimeout(() => { if (wantRef.current) begin(); }, 250); // keep hands-free alive
      } else {
        wantRef.current = false;
        setListening(false);
      }
    };
    recRef.current = rec;
    try { rec.start(); setListening(true); setError(''); } catch { recRef.current = null; }
  }, [Rec, lang]);

  const start = useCallback(() => { wantRef.current = true; begin(); }, [begin]);
  const stop = useCallback(() => { wantRef.current = false; recRef.current?.stop(); setListening(false); }, []);

  // Turning hands-free on starts listening; turning it off stops
  useEffect(() => {
    if (handsFree) start(); else stop();
    return () => { wantRef.current = false; recRef.current?.abort?.(); };
  }, [handsFree, start, stop]);

  return { supported: Boolean(Rec), listening, interim, error, start, stop };
}

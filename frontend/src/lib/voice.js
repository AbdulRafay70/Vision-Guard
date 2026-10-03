import { useCallback, useEffect, useRef, useState } from 'react';

// ── Speech output ───────────────────────────────────────────────────
export function speak(text) {
  try {
    if (!text || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    window.speechSynthesis.speak(u);
  } catch { /* speech unavailable */ }
}

// ── Speech input ────────────────────────────────────────────────────
export function useSpeech(onFinal) {
  const Rec = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState('');
  const recRef = useRef(null);
  const cbRef = useRef(onFinal);
  useEffect(() => { cbRef.current = onFinal; }, [onFinal]);

  const stop = useCallback(() => { recRef.current?.stop(); }, []);

  const start = useCallback(() => {
    if (!Rec || recRef.current) return;
    const rec = new Rec();
    rec.lang = 'en-US';
    rec.interimResults = true;
    rec.continuous = false;
    rec.onresult = (e) => {
      let text = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) cbRef.current?.(r[0].transcript.trim());
        else text += r[0].transcript;
      }
      setInterim(text);
    };
    rec.onend = () => { recRef.current = null; setListening(false); setInterim(''); };
    rec.onerror = () => { recRef.current = null; setListening(false); setInterim(''); };
    recRef.current = rec;
    setListening(true);
    try { rec.start(); } catch { recRef.current = null; setListening(false); }
  }, [Rec]);

  useEffect(() => () => recRef.current?.abort(), []);

  return { supported: !!Rec, listening, interim, start, stop };
}

// ── Intent parsing ──────────────────────────────────────────────────
const WORD_NUM = { one: 1, two: 2, to: 2, too: 2, three: 3, four: 4, for: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10 };
const PAGES = [
  { page: 'dashboard', re: /\b(dashboard|operations|home|overview)\b/, name: 'operations' },
  { page: 'live', re: /\blive( view)?\b/, name: 'live view' },
  { page: 'registry', re: /\b(registry|camera list|all cameras list)\b/, name: 'the camera registry' },
  { page: 'connect', re: /\b(connect|add) (a )?(new )?camera\b/, name: 'connect camera' },
  { page: 'incidents', re: /\b(incidents?|alerts? log|evidence)\b/, name: 'incidents' },
];

const toNum = (s) => (s == null ? null : /^\d+$/.test(s) ? Number(s) : WORD_NUM[s] ?? null);

// "camera 2" → 1-based index; otherwise match by id or name.
function findCamera(text, cameras) {
  const m = text.match(/\b(?:camera|cam|feed)\s*(?:number\s*)?(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b/);
  if (m) {
    const n = toNum(m[1]);
    if (n && cameras[n - 1]) return cameras[n - 1];
  }
  return cameras.find((c) => text.includes(String(c.id).toLowerCase()))
    || cameras.find((c) => c.name && c.name.length > 2 && text.includes(c.name.toLowerCase()))
    || null;
}

function findScope(text, cities) {
  for (const city of cities) {
    for (const area of city.areas) {
      for (const st of area.streets) {
        if (text.includes(st.name.toLowerCase())) return { scope: { cityId: city.id, areaId: area.id, streetId: st.id }, name: st.name };
      }
    }
  }
  for (const city of cities) {
    for (const area of city.areas) {
      if (text.includes(area.name.toLowerCase())) return { scope: { cityId: city.id, areaId: area.id }, name: area.name };
    }
  }
  for (const city of cities) {
    if (text.includes(city.name.toLowerCase())) return { scope: { cityId: city.id }, name: city.name };
  }
  return null;
}

// Console-level commands handled entirely in the browser. Returns null when
// the phrase is not a console command so it can fall through to the backend.
export function parseIntent(raw, { cameras = [], cities = [] } = {}) {
  const t = ` ${String(raw).toLowerCase().replace(/[^\w\s]/g, ' ').replace(/\s+/g, ' ').trim()} `;

  if (/\b(log ?out|sign ?out)\b/.test(t)) return { type: 'logout', say: 'Signing out.' };
  if (/\b(exit|leave|close) full ?screen\b/.test(t)) return { type: 'exitFullscreen', say: 'Exiting full screen.' };
  if (/\bfull ?screen\b/.test(t)) return { type: 'fullscreen', say: 'Full screen.' };
  if (/\bzoom in\b/.test(t)) return { type: 'zoom', dir: 1, say: 'Zooming in.' };
  if (/\bzoom out\b/.test(t)) return { type: 'zoom', dir: -1, say: 'Zooming out.' };
  if (/\b(reset zoom|zoom reset)\b/.test(t)) return { type: 'zoom', dir: 0, say: 'Zoom reset.' };

  const grid = t.match(/\b(?:grid|layout)?\s*(\d|one|two|three|four)\s*(?:by|x|×)\s*(\d|one|two|three|four)\b/);
  if (grid && toNum(grid[1]) === toNum(grid[2]) && [1, 2, 3, 4].includes(toNum(grid[1]))) {
    const n = toNum(grid[1]);
    return { type: 'layout', size: n * n, say: `Showing a ${n} by ${n} grid.` };
  }
  if (/\bsingle view\b/.test(t)) return { type: 'layout', size: 1, say: 'Single view.' };

  const cam = findCamera(t, cameras);
  if (/\b(pin|add)\b.*\b(dashboard|wall)\b/.test(t)) {
    return cam ? { type: 'pin', cameraId: cam.id, say: `${cam.name} pinned to the dashboard.` } : null;
  }
  if (/\b(unpin|remove)\b.*\b(dashboard|wall)\b/.test(t)) {
    return cam ? { type: 'unpin', cameraId: cam.id, say: `${cam.name} removed from the dashboard.` } : null;
  }
  if (/\bdisconnect\b/.test(t)) {
    return cam ? { type: 'disconnect', cameraId: cam.id, say: `Disconnecting ${cam.name}.` } : null;
  }
  if (cam && /\b(show|open|view|switch|go to|focus)\b/.test(t)) {
    return { type: 'focus', cameraId: cam.id, say: `Showing ${cam.name}.` };
  }

  if (/\b(show|view|open|display)\b/.test(t) && /\bcameras?\b/.test(t)) {
    if (/\ball cameras\b/.test(t)) return { type: 'scope', scope: {}, say: 'Showing all cameras.' };
    const sc = findScope(t, cities);
    if (sc) return { type: 'scope', scope: sc.scope, say: `Showing ${sc.name} cameras.` };
  }

  for (const p of PAGES) {
    if (/\b(go to|open|show|switch to|navigate to)\b/.test(t) && p.re.test(t)) return { type: 'navigate', page: p.page, say: `Opening ${p.name}.` };
  }
  return null;
}

// Map the backend interpreter's action JSON to a console intent where one applies.
export function intentFromBackend(command, ctx = {}) {
  if (!command?.action) return null;
  const params = command.params || {};
  switch (command.action) {
    case 'zoom_in': return { type: 'zoom', dir: 1 };
    case 'zoom_out': return { type: 'zoom', dir: -1 };
    case 'show_heatmap': return null;
    case 'switch_camera': {
      const ref = String(params.camera_id ?? params.camera_name ?? '').toLowerCase();
      if (!ref) return null;
      const cams = ctx.cameras || [];
      const cam = cams.find((c) => String(c.id).toLowerCase() === ref || c.name?.toLowerCase() === ref)
        || findCamera(` camera ${ref} `, cams);
      return cam ? { type: 'focus', cameraId: cam.id } : null;
    }
    case 'show_cameras': {
      const zone = String(params.zone || '').toLowerCase();
      if (!zone) return null;
      const sc = findScope(` ${zone} `, ctx.cities || []);
      return sc ? { type: 'scope', scope: sc.scope } : null;
    }
    default: return null;
  }
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, wsUrl } from './lib/api';
import { inScope, useRegistry } from './lib/registry';
import { intentFromBackend, parseIntent, speak } from './lib/voice';
import Login from './pages/Login';
import Shell from './components/Shell';
import Dashboard from './pages/Dashboard';
import LiveView from './pages/LiveView';
import Registry from './pages/Registry';
import ConnectCamera from './pages/ConnectCamera';
import Incidents from './pages/Incidents';

const SESSION_KEY = 'vg.session';
const PINNED_KEY = 'vg.pinned';

function readJSON(storage, key, fallback) {
  try { return JSON.parse(storage.getItem(key)) ?? fallback; } catch { return fallback; }
}
function writeJSON(storage, key, value) {
  try { storage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ }
}

export default function App() {
  const [session, setSession] = useState(() => readJSON(sessionStorage, SESSION_KEY, null));

  const signIn = (s) => { writeJSON(sessionStorage, SESSION_KEY, s); setSession(s); };
  const signOut = useCallback(() => { sessionStorage.removeItem(SESSION_KEY); setSession(null); }, []);

  if (!session) return <Login onSignIn={signIn} />;
  return <Console session={session} onSignOut={signOut} />;
}

function Console({ session, onSignOut }) {
  const registry = useRegistry();
  const [page, setPage] = useState('dashboard');
  const [rawCameras, setRawCameras] = useState([]);
  const [status, setStatus] = useState(null);
  const [online, setOnline] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [voiceLog, setVoiceLog] = useState([]);

  // Live view state — all of it is reachable by voice
  const [scope, setScope] = useState({});
  const [focusId, setFocusId] = useState(null);
  const [layout, setLayout] = useState(4);
  const [zoom, setZoom] = useState(1);
  const [theater, setTheater] = useState(false);
  const [pinned, setPinned] = useState(() => readJSON(localStorage, PINNED_KEY, []));
  useEffect(() => writeJSON(localStorage, PINNED_KEY, pinned), [pinned]);

  // ── Backend polling ──────────────────────────────────────────────
  const refresh = useCallback(async () => {
    try {
      const [cams, st] = await Promise.all([api.cameras(), api.status().catch(() => null)]);
      setRawCameras(Array.isArray(cams) ? cams : []);
      setStatus(st);
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  // ── Alert stream ─────────────────────────────────────────────────
  useEffect(() => {
    let ws;
    let retry;
    let closed = false;
    const connect = () => {
      ws = new WebSocket(wsUrl('/ws/alerts'));
      ws.onmessage = (e) => {
        let msg;
        try { msg = JSON.parse(e.data); } catch { return; }
        if (msg.type === 'NEW_ALERT' || msg.type === 'ACOUSTIC_ALERT') {
          setAlerts((a) => [{ ...msg, id: `${Date.now()}-${Math.random()}`, receivedAt: Date.now() }, ...a].slice(0, 200));
        } else if (msg.type === 'ALERT_NARRATION') {
          setAlerts((a) => {
            const i = a.findIndex((x) => x.event_type === msg.event_type && !x.narration);
            if (i < 0) return a;
            const copy = [...a];
            copy[i] = { ...copy[i], narration: { english: msg.english, urdu: msg.urdu } };
            return copy;
          });
        }
      };
      ws.onclose = () => { if (!closed) retry = setTimeout(connect, 3000); };
    };
    connect();
    return () => { closed = true; clearTimeout(retry); ws?.close(); };
  }, []);

  // ── Derived camera list (backend + location placement) ───────────
  const cameras = useMemo(
    () => rawCameras.map((c) => ({ ...c, placement: registry.placements[c.id] || null })),
    [rawCameras, registry.placements],
  );

  const ctxRef = useRef({ cameras: [], cities: [] });

  const togglePin = useCallback((id) => {
    setPinned((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  }, []);

  const focusCamera = useCallback((id) => {
    // Move the location scope to where the camera is installed so the breadcrumb stays accurate
    const p = ctxRef.current.cameras.find((c) => c.id === id)?.placement;
    setScope((s) => (inScope(p, s) ? s : p ? { cityId: p.cityId, areaId: p.areaId } : {}));
    setFocusId(id);
    setLayout(1);
    setZoom(1);
    setPage('live');
  }, []);

  // ── Voice / command handling ─────────────────────────────────────
  const applyIntent = useCallback(async (intent) => {
    switch (intent.type) {
      case 'navigate': setPage(intent.page); setTheater(false); break;
      case 'focus': focusCamera(intent.cameraId); break;
      case 'scope': setScope(intent.scope); setFocusId(null); setLayout((l) => (l === 1 ? 4 : l)); setPage('live'); break;
      case 'layout': setLayout(intent.size); if (intent.size > 1) setFocusId(null); setPage('live'); break;
      case 'zoom': setZoom((z) => (intent.dir === 0 ? 1 : Math.min(4, Math.max(1, z + intent.dir * 0.5)))); break;
      case 'pin': setPinned((p) => (p.includes(intent.cameraId) ? p : [...p, intent.cameraId])); break;
      case 'unpin': setPinned((p) => p.filter((x) => x !== intent.cameraId)); break;
      case 'fullscreen': setTheater(true); if (page !== 'live' && page !== 'dashboard') setPage('live'); break;
      case 'exitFullscreen': setTheater(false); break;
      case 'disconnect': await api.disconnectCamera(intent.cameraId).catch(() => {}); refresh(); break;
      case 'logout': onSignOut(); break;
      default: break;
    }
  }, [focusCamera, onSignOut, page, refresh]);

  useEffect(() => { ctxRef.current = { cameras, cities: registry.cities }; }, [cameras, registry.cities]);

  const runCommand = useCallback(async (text) => {
    if (!text?.trim()) return;
    const ctx = ctxRef.current;
    const entry = { id: Date.now(), text, at: new Date(), reply: '…', source: 'console' };
    setVoiceLog((l) => [entry, ...l].slice(0, 50));
    const finish = (reply, source) => {
      setVoiceLog((l) => l.map((x) => (x.id === entry.id ? { ...x, reply, source } : x)));
      speak(reply);
    };

    // Console-level commands are handled locally and never reach the backend,
    // so navigation phrases can't trigger side effects like dismissing alerts.
    const local = parseIntent(text, ctx);
    if (local) {
      await applyIntent(local);
      finish(local.say, 'console');
      return;
    }
    try {
      const res = await api.voice(text);
      const intent = intentFromBackend(res.command, ctx);
      if (intent) await applyIntent(intent);
      finish(res.response || res.command?.clarification_question || 'Command executed.', 'backend');
    } catch {
      finish('Command not recognised and the command server is unreachable.', 'error');
    }
  }, [applyIntent]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setTheater(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const view = { scope, setScope, focusId, setFocusId, layout, setLayout, zoom, setZoom, theater, setTheater };
  const common = { cameras, registry, pinned, togglePin, focusCamera };

  return (
    <Shell
      page={page}
      onNavigate={(p) => { setPage(p); setTheater(false); }}
      session={session}
      onSignOut={onSignOut}
      online={online}
      status={status}
      cameras={cameras}
      alerts={alerts}
      voiceLog={voiceLog}
      onCommand={runCommand}
    >
      {page === 'dashboard' && <Dashboard {...common} view={view} status={status} alerts={alerts} voiceLog={voiceLog} onNavigate={setPage} />}
      {page === 'live' && <LiveView {...common} view={view} />}
      {page === 'registry' && <Registry {...common} onRefresh={refresh} onNavigate={setPage} />}
      {page === 'connect' && <ConnectCamera registry={registry} onConnected={(id) => { refresh(); setPinned((p) => (p.includes(id) ? p : [...p, id])); }} />}
      {page === 'incidents' && <Incidents alerts={alerts} />}
    </Shell>
  );
}

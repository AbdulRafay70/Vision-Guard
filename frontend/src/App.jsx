import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api, session, wsUrl } from './lib/api';
import { inScope, useRegistry } from './lib/registry';
import { intentFromBackend, parseIntent, speak } from './lib/voice';
import { can } from './lib/roles';
import Login, { ForcePasswordChange } from './pages/Login';
import Shell from './components/Shell';
import Dashboard from './pages/Dashboard';
import LiveView from './pages/LiveView';
import Registry from './pages/Registry';
import ConnectCamera from './pages/AddDevice';
import Incidents from './pages/Incidents';
import Analytics from './pages/Analytics';
import SystemHealth from './pages/SystemHealth';
import Users from './pages/Users';
import AuditLog from './pages/AuditLog';
import Settings from './pages/Settings';
import DemoFootage from './pages/DemoFootage';

export default function App() {
  const [me, setMe] = useState(null); // { user, preferences }
  const [booting, setBooting] = useState(Boolean(session.token));

  const signOut = useCallback(async (callServer = true) => {
    if (callServer && session.token) await api.logout().catch(() => {});
    session.set('');
    setMe(null);
  }, []);

  useEffect(() => {
    session.onUnauthorized(() => { session.set(''); setMe(null); });
    if (!session.token) return;
    api.me().then(setMe).catch(() => session.set('')).finally(() => setBooting(false));
  }, []);

  const onSignIn = async (res) => {
    session.set(res.token);
    setMe(await api.me());
  };

  if (booting) return <div className="boot">Restoring session…</div>;
  if (!me) return <Login onSignIn={onSignIn} />;
  if (me.user.must_change_password) {
    return <ForcePasswordChange user={me.user} onDone={async () => setMe(await api.me())} onCancel={() => signOut()} />;
  }
  return <Console me={me} onSignOut={() => signOut()} onProfileChange={async () => setMe(await api.me())} />;
}

const DEFAULT_VOICE = { speak: true, handsFree: false, lang: 'en-US' };

function Console({ me, onSignOut, onProfileChange }) {
  const user = me.user;
  const prefs = me.preferences || {};
  const registry = useRegistry(true);
  const [page, setPage] = useState('dashboard');
  const [rawCameras, setRawCameras] = useState([]);
  const [status, setStatus] = useState(null);
  const [online, setOnline] = useState(true);
  const [alerts, setAlerts] = useState([]);
  const [voiceLog, setVoiceLog] = useState([]);
  const [toast, setToast] = useState(null);

  // Live view state — all of it is reachable by voice
  const [scope, setScope] = useState({});
  const [focusId, setFocusId] = useState(null);
  const [layout, setLayout] = useState(prefs.layout || 4);
  const [zoom, setZoom] = useState(1);
  const [theater, setTheater] = useState(false);
  const [pageStep, setPageStep] = useState(0);
  const [pinned, setPinned] = useState(Array.isArray(prefs.pinned) ? prefs.pinned : []);
  const [voice, setVoice] = useState({ ...DEFAULT_VOICE, ...(prefs.voice || {}) });

  // Persist console preferences to the operator's profile (debounced)
  const firstSave = useRef(true);
  useEffect(() => {
    if (firstSave.current) { firstSave.current = false; return undefined; }
    const t = setTimeout(() => { api.savePreferences({ pinned, layout, voice }).catch(() => {}); }, 600);
    return () => clearTimeout(t);
  }, [pinned, layout, voice]);

  const notify = useCallback((text, tone = 'ok') => {
    setToast({ text, tone, id: Date.now() });
  }, []);
  useEffect(() => {
    if (!toast) return undefined;
    const t = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(t);
  }, [toast]);

  // ── Backend polling ──────────────────────────────────────────────
  const refresh = useCallback(async () => {
    try {
      const [cams, st] = await Promise.all([api.cameras(), api.status().catch(() => null)]);
      setRawCameras(Array.isArray(cams) ? cams : []);
      setStatus(st);
      setOnline(true);
    } catch (e) {
      if (e.status !== 401) setOnline(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  // Voice history and recent incidents from the database
  useEffect(() => {
    api.voiceLog(30).then((rows) => setVoiceLog(rows.map((r) => ({
      id: `db-${r.id}`, text: r.text, reply: r.response, source: r.source, at: new Date(r.created_at),
    })))).catch(() => {});
    api.incidents(1).then((rows) => setAlerts(rows.map((r) => ({
      id: r.incident_code, incident_code: r.incident_code, event_type: r.event_type, risk_level: r.risk_level,
      risk_score: r.risk_score, description: r.description, sector: r.sector, camera_id: r.camera_id,
      status: r.status, timestamp: r.timestamp, receivedAt: new Date(r.timestamp).getTime(),
    })))).catch(() => {});
  }, []);

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
          const a = msg.type === 'ACOUSTIC_ALERT'
            ? { event_type: msg.data?.sound_name, risk_level: 'HIGH', description: msg.data?.confidence_boost_str, camera_id: msg.data?.camera_id }
            : msg;
          setAlerts((list) => [{ ...a, status: 'open', id: a.incident_code || `${Date.now()}-${Math.random()}`, receivedAt: Date.now() }, ...list].slice(0, 200));
        } else if (msg.type === 'ALERT_NARRATION') {
          setAlerts((list) => {
            const i = list.findIndex((x) => x.event_type === msg.event_type && !x.narration);
            if (i < 0) return list;
            const copy = [...list];
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

  const cameras = useMemo(
    () => rawCameras.map((c) => ({ ...c, placement: registry.placements[c.id] || null })),
    [rawCameras, registry.placements],
  );

  const ctxRef = useRef({ cameras: [], cities: [] });
  useEffect(() => { ctxRef.current = { cameras, cities: registry.cities }; }, [cameras, registry.cities]);

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

  const cameraAction = useCallback(async (kind, id) => {
    const cam = ctxRef.current.cameras.find((c) => c.id === id);
    try {
      const res = kind === 'start' ? await api.startCamera(id) : await api.stopCamera(id);
      await refresh();
      if (kind === 'start' && res.status !== 'online') throw new Error(res.status_message || 'Camera did not come online');
      return `${cam?.name || id} ${kind === 'start' ? 'is online' : 'stopped'}.`;
    } catch (e) {
      await refresh();
      throw new Error(`${cam?.name || id}: ${e.message}`);
    }
  }, [refresh]);

  // ── Voice / command handling ─────────────────────────────────────
  const allowed = useCallback((p) => (p === 'users' ? can.manageUsers(user) : p === 'audit' ? can.viewAudit(user) : p === 'connect' ? can.manageCameras(user) : true), [user]);

  const applyIntent = useCallback(async (intent) => {
    switch (intent.type) {
      case 'navigate':
        if (!allowed(intent.page)) throw new Error('Your role does not have access to that page.');
        setPage(intent.page); setTheater(false); break;
      case 'focus': focusCamera(intent.cameraId); break;
      case 'scope': setScope(intent.scope); setFocusId(null); setLayout((l) => (l === 1 ? 4 : l)); setPage('live'); break;
      case 'layout': setLayout(intent.size); if (intent.size > 1) setFocusId(null); setPage('live'); break;
      case 'zoom': setZoom((z) => (intent.dir === 0 ? 1 : Math.min(4, Math.max(1, z + intent.dir * 0.5)))); break;
      case 'page': setPageStep((n) => n + intent.dir); break;
      case 'pin': setPinned((p) => (p.includes(intent.cameraId) ? p : [...p, intent.cameraId])); break;
      case 'unpin': setPinned((p) => p.filter((x) => x !== intent.cameraId)); break;
      case 'fullscreen': setTheater(true); setPage((p) => (p === 'dashboard' ? p : 'live')); break;
      case 'exitFullscreen': setTheater(false); break;
      case 'refresh': await refresh(); await registry.reload(); break;
      case 'startCamera':
      case 'stopCamera':
        if (!can.operateCameras(user)) throw new Error('Your role cannot start or stop cameras.');
        return cameraAction(intent.type === 'startCamera' ? 'start' : 'stop', intent.cameraId);
      case 'demo': {
        if (!can.manageCameras(user)) throw new Error('Your role cannot deploy demo footage.');
        const res = await api.deployDemo();
        const ids = res.deployed.map((d) => d.id);
        setPinned((p) => [...p, ...ids.filter((id) => !p.includes(id))]);
        await refresh(); await registry.reload();
        setPage('dashboard');
        return `${res.deployed.filter((d) => d.active).length} demo streams are live on the dashboard.`;
      }
      case 'logout': onSignOut(); break;
      default: break;
    }
    return intent.say;
  }, [allowed, cameraAction, focusCamera, onSignOut, refresh, registry, user]);

  const runCommand = useCallback(async (text) => {
    if (!text?.trim()) return;
    const ctx = ctxRef.current;
    const entry = { id: `local-${Date.now()}`, text, at: new Date(), reply: '…', source: 'console' };
    setVoiceLog((l) => [entry, ...l].slice(0, 100));
    const finish = (reply, source) => {
      setVoiceLog((l) => l.map((x) => (x.id === entry.id ? { ...x, reply, source } : x)));
      if (voice.speak) speak(reply, voice.lang);
    };

    // Console-level commands are handled locally (and logged), so navigation
    // phrases can't trigger backend side effects like dismissing alerts.
    const local = parseIntent(text, ctx);
    if (local) {
      let reply;
      let source = 'console';
      try { reply = (await applyIntent(local)) || local.say; } catch (e) { reply = e.message; source = 'error'; }
      finish(reply, source);
      api.logVoice({ text, action: local.type, response: reply }).catch(() => {});
      return;
    }
    try {
      const res = await api.voice(text);
      const intent = intentFromBackend(res.command, ctx);
      if (intent) await applyIntent(intent).catch(() => {});
      finish(res.response || res.command?.clarification_question || 'Command executed.', 'backend');
    } catch (e) {
      finish(e.status ? e.message : 'Command not recognised and the command server is unreachable.', 'error');
    }
  }, [applyIntent, voice.lang, voice.speak]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setTheater(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const navigate = (p) => { if (allowed(p)) { setPage(p); setTheater(false); } };
  const view = { scope, setScope, focusId, setFocusId, layout, setLayout, zoom, setZoom, theater, setTheater, pageStep };
  const common = { user, cameras, registry, pinned, togglePin, focusCamera, notify, onRefresh: refresh };

  return (
    <Shell
      page={page}
      onNavigate={navigate}
      user={user}
      onSignOut={onSignOut}
      online={online}
      status={status}
      cameras={cameras}
      alerts={alerts}
      voiceLog={voiceLog}
      voice={voice}
      onCommand={runCommand}
      toast={toast}
    >
      {page === 'dashboard' && <Dashboard {...common} view={view} status={status} alerts={alerts} voiceLog={voiceLog} onNavigate={navigate} onLoadDemo={() => applyIntent({ type: 'demo' }).then((m) => notify(m)).catch((e) => notify(e.message, 'bad'))} />}
      {page === 'live' && <LiveView {...common} view={view} />}
      {page === 'registry' && <Registry {...common} cameraAction={cameraAction} onNavigate={navigate} />}
      {page === 'connect' && <ConnectCamera {...common} onConnected={(id) => { refresh(); setPinned((p) => (p.includes(id) ? p : [...p, id])); }} />}
      {page === 'incidents' && <Incidents {...common} liveAlerts={alerts} />}
      {page === 'analytics' && <Analytics {...common} />}
      {page === 'health' && <SystemHealth {...common} status={status} />}
      {page === 'users' && <Users {...common} />}
      {page === 'audit' && <AuditLog {...common} />}
      {page === 'demo' && <DemoFootage {...common} onDeployed={(ids) => setPinned((p) => [...p, ...ids.filter((id) => !p.includes(id))])} />}
      {page === 'settings' && <Settings {...common} voice={voice} setVoice={setVoice} onProfileChange={onProfileChange} />}
    </Shell>
  );
}

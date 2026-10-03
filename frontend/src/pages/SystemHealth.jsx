import { useEffect, useState } from 'react';
import { api } from '../lib/api';

function Meter({ label, value, max = 100, unit = '%', warn = 75, bad = 90 }) {
  const pct = Math.min(100, (value / max) * 100);
  const tone = pct >= bad ? 'bad' : pct >= warn ? 'warn' : 'ok';
  return (
    <div className="meter">
      <div className="meter-top"><span className="label">{label}</span><strong className="mono">{value}{unit}</strong></div>
      <div className="meter-track"><span className={`meter-fill fill-${tone}`} style={{ width: `${pct}%` }} /></div>
    </div>
  );
}

export default function SystemHealth({ cameras, status }) {
  const [t, setT] = useState(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    const load = () => api.telemetry().then((d) => { setT(d); setErr(''); }).catch((e) => setErr(e.message));
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const hw = t?.hardware || {};
  const spec = t?.specialists || {};
  const states = ['online', 'connecting', 'error', 'stopped'].map((s) => [s, cameras.filter((c) => c.status === s).length]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>System health</h1>
          <p className="muted">Live server, AI pipeline and per-camera telemetry. Refreshes every 5 seconds.</p>
        </div>
      </div>
      {err && <div className="notice notice-error">{err}</div>}

      <div className="grid-3">
        <section className="panel">
          <div className="panel-head"><h3>Server</h3><span className="muted small">{hw.gpu_name || '—'}</span></div>
          <div className="meters">
            <Meter label="CPU" value={hw.cpu_percent ?? 0} />
            <Meter label="Memory" value={hw.ram_percent ?? 0} />
            <Meter label="GPU memory" value={hw.vram_mb ?? 0} max={4096} unit=" MB" warn={70} bad={88} />
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>AI pipeline</h3></div>
          <dl className="facts facts-tight">
            <div><dt>Throughput</dt><dd className="mono">{status?.ai_fps != null ? `${Number(status.ai_fps).toFixed(1)} fps` : '—'}</dd></div>
            <div><dt>Context governor</dt><dd>{t?.governor?.decision || '—'}</dd></div>
            {Object.entries(spec).map(([k, v]) => <div key={k}><dt className="cap">{k.replace(/_fps$/, '').replace(/_/g, ' ')}</dt><dd className="mono">{Number(v).toFixed(1)} fps</dd></div>)}
            {!Object.keys(spec).length && <div><dt>Specialist models</dt><dd className="muted">No telemetry reported</dd></div>}
          </dl>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>Camera fleet</h3><span className="muted small">{cameras.length} registered</span></div>
          <dl className="facts facts-tight">
            {states.map(([s, n]) => <div key={s}><dt className="cap">{s === 'error' ? 'Fault' : s}</dt><dd className="mono">{n}</dd></div>)}
            <div><dt>Open alerts</dt><dd className="mono">{status?.active_alerts ?? '—'}</dd></div>
          </dl>
        </section>
      </div>

      <section className="panel">
        <div className="panel-head"><h3>Per-camera stream telemetry</h3></div>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Camera</th><th>Status</th><th className="num">Source fps</th><th className="num">Display fps</th><th className="num">Unique fps</th><th className="num">Avg age</th><th className="num">p95 age</th><th className="num">Dropped</th></tr></thead>
            <tbody>
              {cameras.map((c) => (
                <tr key={c.id}>
                  <td><strong>{c.name}</strong><div className="mono small muted">{c.id}</div></td>
                  <td className="small">{c.status}{c.status !== 'online' && c.status_message ? <div className="muted ellipsis">{c.status_message}</div> : null}</td>
                  {['camera_fps', 'display_fps', 'unique_fps'].map((k) => <td key={k} className="num mono">{c.active ? Number(c.stats?.[k] || 0).toFixed(1) : '—'}</td>)}
                  <td className="num mono">{c.active ? `${Math.round(c.stats?.avg_frame_age_ms || 0)} ms` : '—'}</td>
                  <td className="num mono">{c.active ? `${Math.round(c.stats?.p95_frame_age_ms || 0)} ms` : '—'}</td>
                  <td className="num mono">{c.active ? c.stats?.dropped_stale ?? 0 : '—'}</td>
                </tr>
              ))}
              {!cameras.length && <tr><td colSpan={8} className="empty-line">No cameras registered.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

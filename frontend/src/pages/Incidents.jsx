import { useCallback, useEffect, useMemo, useState } from 'react';
import { api, evidenceUrl } from '../lib/api';
import { can } from '../lib/roles';
import { levelTone, eventName } from '../components/AlertList';
import { fmtAlertTime } from '../lib/time';
import Modal from '../components/Modal';
import { RefreshCw, Download } from '../components/Icons';

const STATUSES = [['', 'All'], ['open', 'Open'], ['acknowledged', 'Acknowledged'], ['resolved', 'Resolved'], ['false_alarm', 'False alarm']];
const STATUS_TAG = { open: 'tag-bad', acknowledged: 'tag-warn', resolved: 'tag-live', false_alarm: 'tag-off' };
const label = (s) => (STATUSES.find(([k]) => k === s)?.[1] || s);

function toCsv(rows) {
  const cols = ['incident_code', 'timestamp', 'event_type', 'risk_level', 'risk_score', 'sector', 'camera_id', 'status', 'acknowledged_by', 'resolved_by', 'notes'];
  const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  return [cols.join(','), ...rows.map((r) => cols.map((c) => esc(r[c])).join(','))].join('\n');
}

export default function Incidents({ user, liveAlerts, cameras, notify }) {
  const [rows, setRows] = useState([]);
  const [days, setDays] = useState(7);
  const [status, setStatus] = useState('');
  const [open, setOpen] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [shot, setShot] = useState(null);

  const load = useCallback(() => {
    api.incidents(days, status).then(setRows).catch((e) => notify(e.message, 'bad'));
  }, [days, status, notify]);

  useEffect(() => { load(); }, [load]);
  // New live alerts are already in the database — reload when one arrives
  useEffect(() => { if (liveAlerts[0]?.incident_code) load(); }, [liveAlerts, load]);
  useEffect(() => {
    const get = () => api.evidence().then((f) => setEvidence(Array.isArray(f) ? f : [])).catch(() => {});
    get();
    const t = setInterval(get, 15000);
    return () => clearInterval(t);
  }, []);

  const camName = useMemo(() => Object.fromEntries(cameras.map((c) => [c.id, c.name])), [cameras]);
  const counts = useMemo(() => Object.fromEntries(STATUSES.map(([k]) => [k, k ? rows.filter((r) => r.status === k).length : rows.length])), [rows]);
  const shown = rows;

  const exportCsv = () => {
    const blob = new Blob([toCsv(shown)], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `visionguard-incidents-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
          <p className="muted">Every alert raised by the AI event engine is recorded here. Acknowledge, resolve or close each one; actions are saved and audited.</p>
        </div>
        <div className="spacer" />
        <select className="select-sm" value={days} onChange={(e) => setDays(Number(e.target.value))}>
          {[1, 7, 30, 90, 365].map((d) => <option key={d} value={d}>Last {d === 1 ? '24 hours' : `${d} days`}</option>)}
        </select>
        <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={14} /> Refresh</button>
        <button className="btn btn-ghost btn-sm" onClick={exportCsv} disabled={!shown.length}><Download size={14} /> Export CSV</button>
      </div>

      <div className="split">
        <section className="panel">
          <div className="panel-head">
            <div className="segmented segmented-sm">
              {STATUSES.map(([k, l]) => <button key={k} className={status === k ? 'is-active' : ''} onClick={() => setStatus(k)}>{l}{!status && <span className="mono muted"> {counts[k]}</span>}</button>)}
            </div>
          </div>
          <div className="table-wrap scroll tall">
            <table className="table">
              <thead><tr><th>Time</th><th>Event</th><th>Risk</th><th>Location</th><th>Status</th></tr></thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.incident_code} className="clickable" onClick={() => setOpen(r)}>
                    <td className="mono small">{new Date(r.timestamp).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })} {fmtAlertTime(r.timestamp)}</td>
                    <td><strong className="cap">{eventName(r.event_type)}</strong><div className="mono small muted">{r.incident_code}</div></td>
                    <td><span className={`tag tag-${levelTone(r.risk_level)}`}>{r.risk_level}</span></td>
                    <td className="small">{r.sector}<div className="muted ellipsis">{camName[r.camera_id] || r.camera_id}</div></td>
                    <td><span className={`tag ${STATUS_TAG[r.status] || 'tag-off'}`}>{label(r.status)}</span></td>
                  </tr>
                ))}
                {shown.length === 0 && <tr><td colSpan={5} className="empty-line">No incidents in this period.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>Evidence frames</h3><span className="muted small">{evidence.length}</span></div>
          <div className="scroll tall">
            {evidence.length === 0 ? <p className="empty-line">No evidence captured yet.</p> : (
              <div className="evidence">
                {evidence.slice(0, 60).map((f) => (
                  <button key={f} onClick={() => setShot(f)}>
                    <img src={evidenceUrl(f)} alt={f} loading="lazy" />
                    <span className="mono small ellipsis">{f}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>

      {open && <IncidentDetail incident={open} user={user} camName={camName} onClose={() => setOpen(null)}
        onChanged={(row) => { setOpen(row); setRows((list) => list.map((x) => (x.incident_code === row.incident_code ? row : x))); notify(`${row.incident_code} → ${label(row.status)}.`); }} notify={notify} />}
      {shot && (
        <div className="lightbox" onClick={() => setShot(null)}>
          <figure onClick={(e) => e.stopPropagation()}>
            <img src={evidenceUrl(shot)} alt={shot} />
            <figcaption className="mono small">{shot}</figcaption>
          </figure>
        </div>
      )}
    </div>
  );
}

function IncidentDetail({ incident: r, user, camName, onClose, onChanged, notify }) {
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const allowed = can.handleIncidents(user);

  const act = async (action) => {
    setBusy(true);
    try { onChanged(await api.incidentAction(r.incident_code, action, note)); setNote(''); } catch (e) { notify(e.message, 'bad'); }
    setBusy(false);
  };

  return (
    <Modal title={`${eventName(r.event_type)} · ${r.incident_code}`} onClose={onClose} wide
      footer={allowed && (
        <>
          {r.status === 'open' && <button className="btn btn-ghost" disabled={busy} onClick={() => act('acknowledge')}>Acknowledge</button>}
          {['open', 'acknowledged'].includes(r.status) && <button className="btn btn-ghost" disabled={busy} onClick={() => act('false_alarm')}>False alarm</button>}
          {['open', 'acknowledged'].includes(r.status) && <button className="btn btn-primary" disabled={busy} onClick={() => act('resolve')}>Resolve</button>}
          {['resolved', 'false_alarm'].includes(r.status) && <button className="btn btn-ghost" disabled={busy} onClick={() => act('reopen')}>Reopen</button>}
          <button className="btn btn-ghost" disabled={busy || !note.trim()} onClick={() => act('note')}>Add note</button>
        </>
      )}>
      <dl className="facts">
        <div><dt>Status</dt><dd><span className={`tag ${STATUS_TAG[r.status] || 'tag-off'}`}>{label(r.status)}</span></dd></div>
        <div><dt>Risk</dt><dd><span className={`tag tag-${levelTone(r.risk_level)}`}>{r.risk_level}</span> <span className="mono">{Math.round((r.risk_score <= 1 ? r.risk_score * 100 : r.risk_score))}</span></dd></div>
        <div><dt>Recorded</dt><dd className="mono">{new Date(r.timestamp).toLocaleString('en-GB')}</dd></div>
        <div><dt>Area</dt><dd>{r.sector}</dd></div>
        <div><dt>Camera</dt><dd>{camName[r.camera_id] || r.camera_id || '—'}</dd></div>
        <div><dt>Source</dt><dd>{r.source}</dd></div>
        {r.acknowledged_by && <div><dt>Acknowledged</dt><dd>{r.acknowledged_by} · <span className="mono small">{r.acknowledged_at}</span></dd></div>}
        {r.resolved_by && <div><dt>Closed</dt><dd>{r.resolved_by} · <span className="mono small">{r.resolved_at}</span></dd></div>}
      </dl>
      {r.description && <p className="incident-desc">{r.description}</p>}
      <div className="field">
        <span>Log</span>
        <pre className="notes">{r.notes || 'No notes yet.'}</pre>
      </div>
      {allowed && <label className="field"><span>Add a note (saved with the next action)</span><textarea rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Police unit 14 dispatched" /></label>}
    </Modal>
  );
}

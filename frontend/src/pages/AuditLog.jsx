import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { RefreshCw } from '../components/Icons';

const GROUPS = [['', 'All activity'], ['login', 'Sign-ins'], ['camera', 'Cameras'], ['incident', 'Incidents'], ['user', 'Operators'], ['password', 'Passwords']];

export default function AuditLog({ notify }) {
  const [rows, setRows] = useState([]);
  const [action, setAction] = useState('');
  const [username, setUsername] = useState('');
  const [tick, setTick] = useState(0);

  useEffect(() => {
    api.audit({ limit: 500, action, username }).then(setRows).catch((e) => notify(e.message, 'bad'));
  }, [action, username, tick, notify]);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Audit log</h1>
          <p className="muted">Every sign-in, camera change, location change, incident decision and account change, with the operator and address.</p>
        </div>
        <div className="spacer" />
        <input className="search" placeholder="Filter by operator" value={username} onChange={(e) => setUsername(e.target.value.trim())} />
        <button className="btn btn-ghost btn-sm" onClick={() => setTick((t) => t + 1)}><RefreshCw size={14} /> Refresh</button>
      </div>
      <div className="segmented segmented-sm">
        {GROUPS.map(([k, l]) => <button key={k} className={action === k ? 'is-active' : ''} onClick={() => setAction(k)}>{l}</button>)}
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Time</th><th>Operator</th><th>Action</th><th>Target</th><th>Detail</th><th>Address</th></tr></thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td className="mono small">{new Date(r.created_at).toLocaleString('en-GB')}</td>
                  <td>{r.username || '—'}</td>
                  <td><span className={`tag ${r.action.includes('fail') || r.action.includes('delete') ? 'tag-bad' : 'tag-info'}`}>{r.action.replace(/_/g, ' ')}</span></td>
                  <td className="mono small">{r.target || '—'}</td>
                  <td className="small ellipsis" title={r.detail}>{r.detail || '—'}</td>
                  <td className="mono small muted">{r.ip || '—'}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={6} className="empty-line">No matching activity.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

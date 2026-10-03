import { useCallback, useEffect, useState } from 'react';
import { api } from '../lib/api';
import { ROLES } from '../lib/roles';
import Modal from '../components/Modal';
import { Plus, Pencil, KeyRound, Trash2 } from '../components/Icons';

const BLANK = { username: '', full_name: '', email: '', role: 'Tactical Operator', department: '', sector: '', password: '' };

export default function Users({ user: me, notify }) {
  const [users, setUsers] = useState([]);
  const [edit, setEdit] = useState(null); // user object or BLANK for new
  const [reset, setReset] = useState(null);

  const load = useCallback(() => api.users().then(setUsers).catch((e) => notify(e.message, 'bad')), [notify]);
  useEffect(() => { load(); }, [load]);

  const toggleStatus = async (u) => {
    try {
      await api.updateUser(u.username, { status: u.status === 'Active' ? 'Suspended' : 'Active', unlock: true });
      notify(`${u.username} ${u.status === 'Active' ? 'suspended' : 'reactivated'}.`);
      load();
    } catch (e) { notify(e.message, 'bad'); }
  };

  const remove = async (u) => {
    if (!window.confirm(`Delete operator ${u.username}? This cannot be undone.`)) return;
    try { await api.deleteUser(u.username); notify(`${u.username} deleted.`); load(); } catch (e) { notify(e.message, 'bad'); }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Operators</h1>
          <p className="muted">Accounts, roles and access. New accounts must set their own password at first sign-in.</p>
        </div>
        <div className="spacer" />
        <button className="btn btn-primary" onClick={() => setEdit(BLANK)}><Plus size={15} /> Add operator</button>
      </div>
      <section className="panel">
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Operator</th><th>Role</th><th>Department / sector</th><th>Status</th><th>Last sign-in</th><th /></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.username}>
                  <td><strong>{u.full_name}</strong><div className="mono small muted">{u.username}{u.email ? ` · ${u.email}` : ''}</div></td>
                  <td>{u.role}</td>
                  <td className="small">{u.department || '—'}<div className="muted">{u.sector}</div></td>
                  <td>
                    <span className={`tag ${u.status === 'Active' ? (u.locked ? 'tag-warn' : 'tag-live') : 'tag-off'}`}>{u.locked ? 'Locked' : u.status}</span>
                    {u.must_change_password && <div className="small muted">Password change pending</div>}
                  </td>
                  <td className="mono small">{u.last_login ? new Date(u.last_login).toLocaleString('en-GB') : 'Never'}</td>
                  <td className="row-actions">
                    <button className="icon-btn" title="Edit" onClick={() => setEdit(u)}><Pencil size={15} /></button>
                    <button className="icon-btn" title="Reset password" onClick={() => setReset(u)}><KeyRound size={15} /></button>
                    {u.username !== me.username && (
                      <button className="btn btn-ghost btn-sm" onClick={() => toggleStatus(u)}>{u.status === 'Active' ? (u.locked ? 'Unlock' : 'Suspend') : 'Reactivate'}</button>
                    )}
                    {u.username !== me.username && u.username !== 'admin' && <button className="icon-btn danger" title="Delete" onClick={() => remove(u)}><Trash2 size={15} /></button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {edit && <UserForm initial={edit} isNew={edit === BLANK} self={edit.username === me.username} onClose={() => setEdit(null)} onSaved={(msg) => { setEdit(null); notify(msg); load(); }} />}
      {reset && <ResetPassword user={reset} onClose={() => setReset(null)} onSaved={(msg) => { setReset(null); notify(msg); load(); }} />}
    </div>
  );
}

function UserForm({ initial, isNew, self, onClose, onSaved }) {
  const [f, setF] = useState(initial);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }));

  const save = async () => {
    setBusy(true); setError('');
    try {
      if (isNew) { await api.createUser(f); await onSaved(`${f.username} created.`); }
      else { await api.updateUser(f.username, f); await onSaved(`${f.username} updated.`); }
    } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Modal title={isNew ? 'Add operator' : `Edit ${initial.username}`} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save'}</button></>}>
      <div className="form-grid two">
        <label className="field"><span>Username</span><input className="mono" value={f.username} onChange={set('username')} disabled={!isNew} autoFocus={isNew} /></label>
        <label className="field"><span>Full name</span><input value={f.full_name} onChange={set('full_name')} /></label>
        <label className="field"><span>Email</span><input value={f.email || ''} onChange={set('email')} /></label>
        <label className="field"><span>Role</span>
          <select value={f.role} onChange={set('role')} disabled={self}>{ROLES.map((r) => <option key={r}>{r}</option>)}</select>
        </label>
        <label className="field"><span>Department</span><input value={f.department || ''} onChange={set('department')} /></label>
        <label className="field"><span>Sector</span><input value={f.sector || ''} onChange={set('sector')} /></label>
        {isNew && <label className="field"><span>Initial password</span><input type="password" autoComplete="new-password" value={f.password} onChange={set('password')} placeholder="At least 8 characters" /></label>}
      </div>
      {error && <div className="notice notice-error">{error}</div>}
    </Modal>
  );
}

function ResetPassword({ user, onClose, onSaved }) {
  const [pw, setPw] = useState('');
  const [error, setError] = useState('');
  const save = async () => {
    try { await api.resetPassword(user.username, pw); await onSaved(`Password reset for ${user.username}. They must change it at next sign-in.`); } catch (e) { setError(e.message); }
  };
  return (
    <Modal title={`Reset password · ${user.username}`} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" onClick={save}>Reset</button></>}>
      <label className="field"><span>Temporary password</span><input type="password" autoComplete="new-password" autoFocus value={pw} onChange={(e) => setPw(e.target.value)} placeholder="At least 8 characters" /></label>
      <p className="muted small">The operator's sign-in lock is cleared and they must choose a new password when they next sign in.</p>
      {error && <div className="notice notice-error">{error}</div>}
    </Modal>
  );
}

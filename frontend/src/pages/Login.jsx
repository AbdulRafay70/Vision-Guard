import { useState } from 'react';
import { api } from '../lib/api';
import { fmtDate, fmtTime, useClock } from '../lib/time';
import Brand from '../components/Brand';
import { Lock, User, CircleAlert } from '../components/Icons';

const STATIONS = ['Central Command — Karachi', 'Sector Control — South', 'Sector Control — East', 'Sector Control — West'];

export default function Login({ onSignIn }) {
  const now = useClock();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [station, setStation] = useState(STATIONS[0]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!username || !password) { setError('Enter your operator ID and password.'); return; }
    setBusy(true);
    try {
      const res = await api.login(username, password, station);
      await onSignIn(res);
    } catch (err) {
      setError(err.status ? err.message : 'Unable to reach the authentication server.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="classification">Restricted · Authorised personnel only · All activity is logged</div>
      <div className="login-body">
        <section className="login-identity">
          <div className="login-mark"><Brand size={44} /></div>
          <p className="eyebrow">Integrated Surveillance Network</p>
          <h1>VisionGuard<br />Command Center</h1>
          <dl className="login-facts">
            <div><dt>Date</dt><dd>{fmtDate(now)}</dd></div>
            <div><dt>Local time</dt><dd className="mono">{fmtTime(now)}</dd></div>
            <div><dt>Terminal</dt><dd className="mono">{window.location.host || 'local'}</dd></div>
          </dl>
        </section>

        <form className="login-form" onSubmit={submit} noValidate>
          <h2>Operator sign-in</h2>
          <p className="muted">Use the credentials issued by your command post.</p>

          <label className="field">
            <span>Operator ID</span>
            <div className="input-icon">
              <User size={16} />
              <input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} />
            </div>
          </label>
          <label className="field">
            <span>Password</span>
            <div className="input-icon">
              <Lock size={16} />
              <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </div>
          </label>
          <label className="field">
            <span>Command post</span>
            <select value={station} onChange={(e) => setStation(e.target.value)}>
              {STATIONS.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>

          {error && <div className="notice notice-error"><CircleAlert size={16} />{error}</div>}

          <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Verifying…' : 'Sign in'}</button>
          <p className="fineprint">Unauthorised access to this system is an offence. Sessions expire after 12 hours or when the browser tab is closed. Five failed attempts lock the account for 15 minutes.</p>
        </form>
      </div>
    </div>
  );
}

export function ForcePasswordChange({ user, onDone, onCancel }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (next.length < 8) { setError('New password must be at least 8 characters.'); return; }
    if (next !== confirm) { setError('The new passwords do not match.'); return; }
    setBusy(true);
    try { await api.changePassword(current, next); await onDone(); } catch (err) { setError(err.message); }
    setBusy(false);
  };

  return (
    <div className="login">
      <div className="classification">Restricted · Authorised personnel only · All activity is logged</div>
      <div className="login-body single">
        <form className="login-form" onSubmit={submit} noValidate>
          <h2>Set a new password</h2>
          <p className="muted">Signed in as <strong>{user.username}</strong>. Your password was issued by an administrator and must be changed before you continue.</p>
          <label className="field"><span>Current password</span><input type="password" autoComplete="current-password" autoFocus value={current} onChange={(e) => setCurrent(e.target.value)} /></label>
          <label className="field"><span>New password</span><input type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} /></label>
          <label className="field"><span>Confirm new password</span><input type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} /></label>
          {error && <div className="notice notice-error"><CircleAlert size={16} />{error}</div>}
          <button className="btn btn-primary btn-block" disabled={busy}>{busy ? 'Saving…' : 'Change password and continue'}</button>
          <button type="button" className="btn btn-ghost btn-block" onClick={onCancel}>Sign out</button>
        </form>
      </div>
    </div>
  );
}

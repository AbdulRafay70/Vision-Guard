import { useState } from 'react';
import { api } from '../lib/api';
import { speak, WAKE_WORDS } from '../lib/voice';

const LANGS = [['en-US', 'English (US)'], ['en-GB', 'English (UK)'], ['en-IN', 'English (South Asia)'], ['ur-PK', 'Urdu']];

export default function Settings({ user, voice, setVoice, notify }) {
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' });
  const [busy, setBusy] = useState(false);
  const setP = (k) => (e) => setPw((x) => ({ ...x, [k]: e.target.value }));

  const changePassword = async (e) => {
    e.preventDefault();
    if (pw.next !== pw.confirm) { notify('The new passwords do not match.', 'bad'); return; }
    setBusy(true);
    try { await api.changePassword(pw.current, pw.next); setPw({ current: '', next: '', confirm: '' }); notify('Password changed.'); } catch (err) { notify(err.message, 'bad'); }
    setBusy(false);
  };

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Settings</h1>
          <p className="muted">Your profile and console preferences. Preferences are saved to your operator account and follow you to any workstation.</p>
        </div>
      </div>

      <section className="panel form-section">
        <h3>Profile</h3>
        <dl className="facts">
          <div><dt>Username</dt><dd className="mono">{user.username}</dd></div>
          <div><dt>Name</dt><dd>{user.full_name}</dd></div>
          <div><dt>Role</dt><dd>{user.role}</dd></div>
          <div><dt>Department</dt><dd>{user.department || '—'}</dd></div>
          <div><dt>Command post</dt><dd>{user.station || '—'}</dd></div>
          <div><dt>Last sign-in</dt><dd className="mono small">{user.last_login ? new Date(user.last_login).toLocaleString('en-GB') : '—'}</dd></div>
        </dl>
      </section>

      <section className="panel form-section">
        <h3>Voice control</h3>
        <label className="check">
          <input type="checkbox" checked={voice.handsFree} onChange={(e) => setVoice((v) => ({ ...v, handsFree: e.target.checked }))} />
          <span><strong>Hands-free mode</strong><br /><span className="muted small">The microphone stays on. Start each command with a wake word: {WAKE_WORDS.map((w) => `“${w}”`).join(', ')}. Example: “Guard, show camera 2”.</span></span>
        </label>
        <label className="check">
          <input type="checkbox" checked={voice.speak} onChange={(e) => setVoice((v) => ({ ...v, speak: e.target.checked }))} />
          <span><strong>Speak replies aloud</strong><br /><span className="muted small">The console reads each command result back.</span></span>
        </label>
        <div className="form-grid two">
          <label className="field"><span>Recognition language</span>
            <select value={voice.lang} onChange={(e) => setVoice((v) => ({ ...v, lang: e.target.value }))}>{LANGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          </label>
          <div className="field"><span>Test</span><button type="button" className="btn btn-ghost" onClick={() => speak('VisionGuard voice output is working.', voice.lang)}>Play test phrase</button></div>
        </div>
        <p className="muted small">Voice recognition uses the browser's speech service (Chrome or Edge) and needs microphone permission. It only works on <span className="mono">localhost</span> or an HTTPS address.</p>
      </section>

      <form className="panel form-section" onSubmit={changePassword}>
        <h3>Change password</h3>
        <div className="form-grid three">
          <label className="field"><span>Current password</span><input type="password" autoComplete="current-password" value={pw.current} onChange={setP('current')} /></label>
          <label className="field"><span>New password</span><input type="password" autoComplete="new-password" value={pw.next} onChange={setP('next')} /></label>
          <label className="field"><span>Confirm</span><input type="password" autoComplete="new-password" value={pw.confirm} onChange={setP('confirm')} /></label>
        </div>
        <div><button className="btn btn-primary" disabled={busy || !pw.current || !pw.next}>Change password</button></div>
      </form>
    </div>
  );
}

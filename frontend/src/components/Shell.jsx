import { useEffect, useRef, useState } from 'react';
import Brand from './Brand';
import { fmtDate, fmtTime, useClock } from '../lib/time';
import { useSpeech } from '../lib/voice';
import { LayoutDashboard, MonitorPlay, List, PlugZap, ShieldAlert, Mic, MicOff, LogOut } from './Icons';

const NAV = [
  { id: 'dashboard', label: 'Operations', icon: LayoutDashboard },
  { id: 'live', label: 'Live view', icon: MonitorPlay },
  { id: 'registry', label: 'Camera registry', icon: List },
  { id: 'connect', label: 'Connect camera', icon: PlugZap },
  { id: 'incidents', label: 'Incidents', icon: ShieldAlert },
];

export default function Shell({ page, onNavigate, session, onSignOut, online, status, cameras, alerts, voiceLog, onCommand, children }) {
  const now = useClock();
  const active = cameras.filter((c) => c.active).length;
  const recentAlerts = alerts.filter((a) => Date.now() - a.receivedAt < 15 * 60 * 1000).length;

  return (
    <div className="shell">
      <aside className="rail">
        <div className="rail-brand">
          <Brand size={26} />
          <div>
            <strong>VisionGuard</strong>
            <span>Command Center</span>
          </div>
        </div>
        <nav>
          {NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} className={`rail-link ${page === id ? 'is-active' : ''}`} onClick={() => onNavigate(id)}>
              <Icon size={17} strokeWidth={1.75} />
              <span>{label}</span>
              {id === 'incidents' && recentAlerts > 0 && <em className="count">{recentAlerts}</em>}
            </button>
          ))}
        </nav>
        <div className="rail-foot">
          <div className="operator">
            <span className="label">Operator</span>
            <strong>{session.user}</strong>
            <span className="muted small">{session.station}</span>
          </div>
          <button className="btn btn-ghost btn-block" onClick={onSignOut}><LogOut size={15} /> Sign out</button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <CommandBar onCommand={onCommand} last={voiceLog[0]} />
          <div className="topbar-stats">
            <Stat label="Link" value={online ? 'Online' : 'Offline'} tone={online ? 'ok' : 'bad'} />
            <Stat label="Cameras" value={`${active}/${cameras.length}`} />
            <Stat label="AI FPS" value={status?.ai_fps != null ? Number(status.ai_fps).toFixed(1) : '—'} />
            <Stat label={fmtDate(now)} value={fmtTime(now)} mono />
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

function Stat({ label, value, tone, mono }) {
  return (
    <div className="tstat">
      <span className="label">{label}</span>
      <strong className={`${tone ? `tone-${tone}` : ''} ${mono ? 'mono' : ''}`}>{tone && <i className={`dot dot-${tone}`} />}{value}</strong>
    </div>
  );
}

function CommandBar({ onCommand, last }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);
  const { supported, listening, interim, start, stop } = useSpeech(onCommand);

  // "V" toggles the microphone when the operator is not typing; "/" focuses the command line.
  useEffect(() => {
    const onKey = (e) => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
      if (typing || e.ctrlKey || e.metaKey || e.altKey) return;
      if (e.key === 'v' || e.key === 'V') { e.preventDefault(); if (listening) stop(); else start(); }
      if (e.key === '/') { e.preventDefault(); inputRef.current?.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [listening, start, stop]);

  const submit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onCommand(text.trim());
    setText('');
  };

  return (
    <form className={`cmdbar ${listening ? 'is-listening' : ''}`} onSubmit={submit}>
      <button
        type="button"
        className="cmd-mic"
        onClick={listening ? stop : start}
        disabled={!supported}
        title={supported ? 'Voice command (V)' : 'Speech recognition is not supported in this browser'}
      >
        {listening ? <Mic size={16} /> : <MicOff size={16} />}
      </button>
      <input
        ref={inputRef}
        value={listening ? interim : text}
        onChange={(e) => setText(e.target.value)}
        placeholder={listening ? 'Listening…' : 'Speak (V) or type a command — e.g. “show Saddar cameras”'}
        readOnly={listening}
      />
      {last && !listening && (
        <span className={`cmd-reply ${last.source === 'error' ? 'tone-bad' : ''}`} title={last.reply}>{last.reply}</span>
      )}
    </form>
  );
}

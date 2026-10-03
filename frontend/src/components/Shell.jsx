import { useEffect, useRef, useState } from 'react';
import Brand from './Brand';
import { fmtDate, fmtTime, useClock } from '../lib/time';
import { useSpeech } from '../lib/voice';
import { can } from '../lib/roles';
import {
  LayoutDashboard, MonitorPlay, List, PlugZap, ShieldAlert, Mic, MicOff, LogOut, BarChart3, Activity,
  Users, ScrollText, Settings, Ear, Check, CircleAlert,
} from './Icons';

const NAV = [
  { group: 'Monitoring' },
  { id: 'dashboard', label: 'Operations', icon: LayoutDashboard },
  { id: 'live', label: 'Live view', icon: MonitorPlay },
  { id: 'incidents', label: 'Incidents', icon: ShieldAlert },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { group: 'Network' },
  { id: 'registry', label: 'Camera registry', icon: List },
  { id: 'connect', label: 'Connect camera', icon: PlugZap, when: can.manageCameras },
  { id: 'health', label: 'System health', icon: Activity },
  { group: 'Administration' },
  { id: 'users', label: 'Operators', icon: Users, when: can.manageUsers },
  { id: 'audit', label: 'Audit log', icon: ScrollText, when: can.viewAudit },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Shell({ page, onNavigate, user, onSignOut, online, status, cameras, alerts, voiceLog, voice, onCommand, toast, children }) {
  const now = useClock();
  const active = cameras.filter((c) => c.active).length;
  const openAlerts = alerts.filter((a) => a.status === 'open').length;
  const items = NAV.filter((n) => !n.when || n.when(user));

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
          {items.map((n, i) => {
            if (n.group) {
              const next = items[i + 1];
              return next && !next.group ? <span key={n.group} className="rail-group">{n.group}</span> : null;
            }
            const Icon = n.icon;
            return (
              <button key={n.id} className={`rail-link ${page === n.id ? 'is-active' : ''}`} onClick={() => onNavigate(n.id)}>
                <Icon size={17} strokeWidth={1.75} />
                <span>{n.label}</span>
                {n.id === 'incidents' && openAlerts > 0 && <em className="count">{openAlerts}</em>}
              </button>
            );
          })}
        </nav>
        <div className="rail-foot">
          <div className="operator">
            <span className="label">Operator</span>
            <strong>{user.full_name || user.username}</strong>
            <span className="muted small">{user.role}{user.station ? ` · ${user.station}` : ''}</span>
          </div>
          <button className="btn btn-ghost btn-block" onClick={onSignOut}><LogOut size={15} /> Sign out</button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <CommandBar onCommand={onCommand} last={voiceLog[0]} voice={voice} />
          <div className="topbar-stats">
            <Stat label="Link" value={online ? 'Online' : 'Offline'} tone={online ? 'ok' : 'bad'} />
            <Stat label="Cameras" value={`${active}/${cameras.length}`} />
            <Stat label="AI FPS" value={status?.ai_fps != null ? Number(status.ai_fps).toFixed(1) : '—'} />
            <Stat label={fmtDate(now)} value={fmtTime(now)} mono />
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
      {toast && (
        <div key={toast.id} className={`toast toast-${toast.tone}`} role="status">
          {toast.tone === 'ok' ? <Check size={16} /> : <CircleAlert size={16} />}{toast.text}
        </div>
      )}
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

function CommandBar({ onCommand, last, voice }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);
  const { supported, listening, interim, error, start, stop } = useSpeech(onCommand, { handsFree: voice.handsFree, lang: voice.lang });

  // "V" toggles the microphone when the operator is not typing; "/" focuses the command line.
  useEffect(() => {
    const onKey = (e) => {
      const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
      if (typing || e.ctrlKey || e.metaKey || e.altKey || voice.handsFree) return;
      if (e.key === 'v' || e.key === 'V') { e.preventDefault(); if (listening) stop(); else start(); }
      if (e.key === '/') { e.preventDefault(); inputRef.current?.focus(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [listening, start, stop, voice.handsFree]);

  const submit = (e) => {
    e.preventDefault();
    if (!text.trim()) return;
    onCommand(text.trim());
    setText('');
  };

  const hint = !supported
    ? 'Voice needs Chrome or Edge — type a command'
    : voice.handsFree ? 'Hands-free: say “Guard, …” — or type a command'
      : 'Speak (V) or type a command — e.g. “show Saddar cameras”';

  return (
    <form className={`cmdbar ${listening ? 'is-listening' : ''} ${voice.handsFree ? 'is-handsfree' : ''}`} onSubmit={submit}>
      <button
        type="button"
        className="cmd-mic"
        onClick={listening ? stop : start}
        disabled={!supported}
        title={supported ? (voice.handsFree ? 'Hands-free listening (change in Settings)' : 'Voice command (V)') : 'Speech recognition is not supported in this browser'}
      >
        {voice.handsFree ? <Ear size={16} /> : listening ? <Mic size={16} /> : <MicOff size={16} />}
      </button>
      <input
        ref={inputRef}
        value={listening && interim ? interim : text}
        onChange={(e) => setText(e.target.value)}
        placeholder={listening && !voice.handsFree ? 'Listening…' : hint}
      />
      {(error || last) && (
        <span className={`cmd-reply ${error || last?.source === 'error' ? 'tone-bad' : ''}`} title={error || last.reply}>{error || last.reply}</span>
      )}
    </form>
  );
}

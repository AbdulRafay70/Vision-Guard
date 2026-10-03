import { fmtAlertTime } from '../lib/time';

export const levelTone = (level) => {
  const l = String(level || '').toUpperCase();
  if (l.includes('CRIT') || l.includes('HIGH')) return 'bad';
  if (l.includes('MED') || l.includes('ELEV')) return 'warn';
  return 'info';
};

export const eventName = (t) => String(t || 'Event').replace(/_/g, ' ');

export default function AlertList({ alerts, limit, empty = 'No alerts received this session.' }) {
  const items = limit ? alerts.slice(0, limit) : alerts;
  if (items.length === 0) return <p className="empty-line">{empty}</p>;
  return (
    <ol className="alerts">
      {items.map((a) => (
        <li key={a.id} className={`alert tone-border-${levelTone(a.risk_level)}`}>
          <div className="alert-top">
            <span className={`tag tag-${levelTone(a.risk_level)}`}>{a.risk_level || 'Info'}</span>
            <strong className="cap">{eventName(a.event_type)}</strong>{a.simulated && <span className="tag tag-off sim-chip">sim</span>}
            <span className="mono small muted">{fmtAlertTime(a.timestamp ?? a.receivedAt)}</span>
          </div>
          {a.description && <p>{a.description}</p>}
          {a.narration?.urdu && <p className="urdu" dir="rtl">{a.narration.urdu}</p>}
          {(a.department || a.risk_score != null) && (
            <div className="alert-meta mono small">
              {a.department && <span>Route: {a.department}{a.dial ? ` · ${a.dial}` : ''}</span>}
              {a.risk_score != null && <span>Risk {Math.round(a.risk_score <= 1 ? a.risk_score * 100 : a.risk_score)}</span>}
            </div>
          )}
        </li>
      ))}
    </ol>
  );
}

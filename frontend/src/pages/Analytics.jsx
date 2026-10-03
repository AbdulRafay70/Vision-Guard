import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Columns, Ranked } from '../components/Charts';
import { eventName } from '../components/AlertList';

const RANGES = [7, 30, 90];

export default function Analytics({ notify }) {
  const [days, setDays] = useState(30);
  const [stats, setStats] = useState(null);
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    api.incidentStats(days).then(setStats).catch((e) => notify(e.message, 'bad'));
  }, [days, notify]);

  const s = stats;
  const resolved = s ? (s.by_status.find((x) => x.name === 'resolved')?.count || 0) : 0;
  const falseAlarms = s ? (s.by_status.find((x) => x.name === 'false_alarm')?.count || 0) : 0;
  const high = s ? s.by_level.filter((x) => /CRIT|HIGH/.test(x.name)).reduce((n, x) => n + x.count, 0) : 0;
  const peak = s ? s.by_hour.reduce((a, b) => (b.count > a.count ? b : a), { hour: 0, count: 0 }) : null;

  const daily = (s?.daily || []).map((d) => {
    const dt = new Date(d.date);
    return { key: d.date, value: d.count, label: dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' }), tip: dt.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }) };
  });
  const hourly = (s?.by_hour || []).map((h) => ({ key: h.hour, value: h.count, label: String(h.hour).padStart(2, '0'), tip: `${String(h.hour).padStart(2, '0')}:00–${String(h.hour).padStart(2, '0')}:59` }));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Analytics</h1>
          <p className="muted">Incident trends computed from the incident database.</p>
        </div>
        <div className="spacer" />
        <div className="segmented segmented-sm">
          {RANGES.map((d) => <button key={d} className={days === d ? 'is-active' : ''} onClick={() => setDays(d)}>{d} days</button>)}
        </div>
      </div>

      <div className="kpis">
        <div className="kpi"><span className="label">Incidents</span><strong>{s ? s.total : '—'}</strong><span className="muted small">last {days} days</span></div>
        <div className="kpi"><span className="label">Still open</span><strong className={s?.open ? 'tone-warn' : ''}>{s ? s.open : '—'}</strong><span className="muted small">awaiting action</span></div>
        <div className="kpi"><span className="label">High / critical</span><strong>{s ? high : '—'}</strong><span className="muted small">{s && s.total ? `${Math.round((high / s.total) * 100)}% of all` : '—'}</span></div>
        <div className="kpi"><span className="label">Peak hour</span><strong>{peak && peak.count ? `${String(peak.hour).padStart(2, '0')}:00` : '—'}</strong><span className="muted small">{s ? `${resolved} resolved · ${falseAlarms} false alarms` : ''}</span></div>
      </div>

      <section className="panel">
        <div className="panel-head"><h3>Incidents per day</h3><div className="spacer" /><button className="link" onClick={() => setShowTable((v) => !v)}>{showTable ? 'Hide table' : 'Show table'}</button></div>
        <div className="chart-pad"><Columns data={daily} tickEvery={Math.ceil(daily.length / 10)} /></div>
        {showTable && (
          <div className="table-wrap"><table className="table"><thead><tr><th>Date</th><th className="num">Incidents</th></tr></thead>
            <tbody>{daily.filter((d) => d.value).map((d) => <tr key={d.key}><td>{d.tip}</td><td className="num mono">{d.value}</td></tr>)}</tbody></table></div>
        )}
      </section>

      <div className="grid-3">
        <section className="panel">
          <div className="panel-head"><h3>By event type</h3></div>
          <div className="chart-pad"><Ranked data={s?.by_type || []} format={(n) => eventName(n)} /></div>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>By area</h3></div>
          <div className="chart-pad"><Ranked data={s?.by_sector || []} /></div>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>Time of day</h3><span className="muted small">all days combined</span></div>
          <div className="chart-pad"><Columns data={hourly} height={140} tickEvery={3} /></div>
        </section>
      </div>
    </div>
  );
}

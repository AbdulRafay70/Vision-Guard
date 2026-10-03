import CameraTile from '../components/CameraTile';
import AlertList from '../components/AlertList';
import { locationLabel } from '../lib/cameras';
import { inScope } from '../lib/registry';
import { fmtTime } from '../lib/time';
import { Pin, Maximize2, Minimize2 } from '../components/Icons';
import { can } from '../lib/roles';

export default function Dashboard({ user, cameras, registry, pinned, togglePin, focusCamera, view, status, alerts, voiceLog, onNavigate, onLoadDemo }) {
  const wall = pinned.map((id) => cameras.find((c) => c.id === id)).filter(Boolean);
  const cols = wall.length <= 1 ? 1 : wall.length <= 4 ? 2 : wall.length <= 9 ? 3 : 4;
  const slots = Math.max(cols * cols, wall.length);

  const active = cameras.filter((c) => c.active).length;
  const lastHour = alerts.filter((a) => Date.now() - a.receivedAt < 3600 * 1000);
  const critical = lastHour.filter((a) => /CRIT|HIGH/i.test(a.risk_level || '')).length;

  const areaRows = registry.cities.flatMap((city) =>
    city.areas.map((area) => {
      const cams = cameras.filter((c) => inScope(c.placement, { cityId: city.id, areaId: area.id }));
      return { key: area.id, city: city.name, area: area.name, total: cams.length, live: cams.filter((c) => c.active).length, streets: area.streets.length, scope: { cityId: city.id, areaId: area.id } };
    }),
  ).filter((r) => r.total > 0 || r.streets > 0);

  return (
    <div className={`dash ${view.theater ? 'is-theater' : ''}`}>
      <div className="kpis">
        <Kpi label="Cameras online" value={active} sub={`of ${cameras.length} registered`} />
        <Kpi label="Alerts · last hour" value={lastHour.length} sub={`${critical} high / critical`} tone={critical ? 'bad' : null} />
        <Kpi label="Active incidents" value={status?.active_alerts ?? '—'} sub="open in event engine" tone={status?.active_alerts ? 'warn' : null} />
        <Kpi label="AI throughput" value={status?.ai_fps != null ? Number(status.ai_fps).toFixed(1) : '—'} sub="frames per second" />
      </div>

      <div className="dash-grid">
        <section className="panel dash-wall">
          <div className="panel-head">
            <h3>Monitoring wall</h3>
            <span className="muted small">{wall.length} pinned</span>
            <div className="spacer" />
            <button className="icon-btn" title={view.theater ? 'Exit full screen' : 'Full screen'} onClick={() => view.setTheater(!view.theater)}>
              {view.theater ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          </div>
          {wall.length === 0 ? (
            <div className="empty-state">
              <Pin size={20} />
              <p>No cameras on the wall yet.</p>
              <p className="muted small">Pin cameras from Live view or the registry, or say “add camera 1 to dashboard”.</p>
              <div className="row-gap">
                <button className="btn btn-ghost btn-sm" onClick={() => onNavigate('live')}>Open live view</button>
                {can.manageCameras(user) && <button className="btn btn-primary btn-sm" onClick={onLoadDemo}>Stream demo footage</button>}
              </div>
            </div>
          ) : (
            <div className="wall" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
              {Array.from({ length: slots }, (_, i) => wall[i]).map((cam, i) => (
                <CameraTile
                  key={cam ? cam.id : `e${i}`}
                  camera={cam}
                  index={cam ? cameras.indexOf(cam) + 1 : null}
                  location={cam && locationLabel(registry.cities, cam.placement)}
                  pinned
                  onTogglePin={togglePin}
                  onFocus={focusCamera}
                  compact={cols >= 4}
                />
              ))}
            </div>
          )}
        </section>

        <section className="panel dash-alerts">
          <div className="panel-head">
            <h3>Alert feed</h3>
            <div className="spacer" />
            <button className="link" onClick={() => onNavigate('incidents')}>All incidents</button>
          </div>
          <div className="scroll"><AlertList alerts={alerts} limit={25} /></div>
        </section>

        <section className="panel dash-areas">
          <div className="panel-head"><h3>Coverage by area</h3></div>
          <table className="table">
            <thead><tr><th>Area</th><th>City</th><th className="num">Streets</th><th className="num">Live</th><th className="num">Total</th></tr></thead>
            <tbody>
              {areaRows.map((r) => (
                <tr key={r.key} className="clickable" onClick={() => { view.setScope(r.scope); view.setFocusId(null); onNavigate('live'); }}>
                  <td>{r.area}</td><td className="muted">{r.city}</td>
                  <td className="num mono">{r.streets}</td>
                  <td className="num mono">{r.live}</td>
                  <td className="num mono">{r.total}</td>
                </tr>
              ))}
              {areaRows.length === 0 && <tr><td colSpan={5} className="empty-line">No cameras assigned to areas yet.</td></tr>}
            </tbody>
          </table>
        </section>

        <section className="panel dash-voice">
          <div className="panel-head"><h3>Command log</h3><span className="muted small">Press V to speak</span></div>
          <div className="scroll">
            {voiceLog.length === 0 ? (
              <div className="hints">
                <p className="muted small">Try:</p>
                <ul>
                  <li>“Show camera 2”</li>
                  <li>“Show Clifton cameras”</li>
                  <li>“Grid three by three”</li>
                  <li>“Add camera 1 to dashboard”</li>
                  <li>“Zoom in” · “Full screen” · “Next page”</li>
                  <li>“Stop camera 3” · “Start Boat Basin”</li>
                  <li>“Open analytics” · “Confirm alert”</li>
                  <li>“Load demo videos”</li>
                  <li>“What's going on?” · “System health”</li>
                </ul>
              </div>
            ) : (
              <ol className="vlog">
                {voiceLog.map((v) => (
                  <li key={v.id}>
                    <span className="mono small muted">{fmtTime(v.at)}</span>
                    <p className="vlog-q">{v.text}</p>
                    <p className={`vlog-a ${v.source === 'error' ? 'tone-bad' : ''}`}>{v.reply}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function Kpi({ label, value, sub, tone }) {
  return (
    <div className="kpi">
      <span className="label">{label}</span>
      <strong className={tone ? `tone-${tone}` : ''}>{value}</strong>
      <span className="muted small">{sub}</span>
    </div>
  );
}

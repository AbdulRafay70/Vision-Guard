import { useEffect, useState } from 'react';
import { api, evidenceUrl } from '../lib/api';
import AlertList, { levelTone } from '../components/AlertList';
import { X } from '../components/Icons';

const FILTERS = ['All', 'High', 'Medium', 'Low'];

export default function Incidents({ alerts }) {
  const [filter, setFilter] = useState('All');
  const [evidence, setEvidence] = useState([]);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    const load = () => api.evidence().then((f) => setEvidence(Array.isArray(f) ? f : [])).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  const tone = { High: 'bad', Medium: 'warn', Low: 'info' }[filter];
  const shown = filter === 'All' ? alerts : alerts.filter((a) => levelTone(a.risk_level) === tone);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
          <p className="muted">Alerts raised by the AI event engine this session, and evidence frames captured on disk.</p>
        </div>
      </div>
      <div className="split">
        <section className="panel">
          <div className="panel-head">
            <h3>Alert log</h3>
            <span className="muted small">{shown.length}</span>
            <div className="spacer" />
            <div className="segmented segmented-sm">
              {FILTERS.map((f) => <button key={f} className={filter === f ? 'is-active' : ''} onClick={() => setFilter(f)}>{f}</button>)}
            </div>
          </div>
          <div className="scroll tall"><AlertList alerts={shown} /></div>
        </section>
        <section className="panel">
          <div className="panel-head"><h3>Evidence frames</h3><span className="muted small">{evidence.length}</span></div>
          <div className="scroll tall">
            {evidence.length === 0 ? <p className="empty-line">No evidence captured yet.</p> : (
              <div className="evidence">
                {evidence.slice(0, 60).map((f) => (
                  <button key={f} onClick={() => setOpen(f)}>
                    <img src={evidenceUrl(f)} alt={f} loading="lazy" />
                    <span className="mono small ellipsis">{f}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
      {open && (
        <div className="lightbox" onClick={() => setOpen(null)}>
          <figure onClick={(e) => e.stopPropagation()}>
            <img src={evidenceUrl(open)} alt={open} />
            <figcaption className="mono small">{open}<button className="icon-btn" onClick={() => setOpen(null)}><X size={15} /></button></figcaption>
          </figure>
        </div>
      )}
    </div>
  );
}

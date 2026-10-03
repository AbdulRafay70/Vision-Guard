import { useState } from 'react';

// Single-series column chart with hover tooltip. data: [{ key, label, value, tip }]
export function Columns({ data, height = 160, unit = 'incidents', tickEvery = 1 }) {
  const [hover, setHover] = useState(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const nice = niceMax(max);
  return (
    <div className="colchart" style={{ height }} onMouseLeave={() => setHover(null)}>
      <div className="colchart-grid">
        {[1, 0.5, 0].map((f) => <div key={f} className="gridline" style={{ bottom: `${f * 100}%` }}><span className="mono">{Math.round(nice * f)}</span></div>)}
      </div>
      <div className="colchart-bars" role="img" aria-label={`Column chart of ${unit}`}>
        {data.map((d, i) => (
          <div key={d.key} className={`col ${hover === i ? 'is-hover' : ''}`} onMouseEnter={() => setHover(i)}>
            <div className="col-bar" style={{ height: `${(d.value / nice) * 100}%` }} />
            <span className="col-label mono">{i % tickEvery === 0 ? d.label : ''}</span>
          </div>
        ))}
      </div>
      {hover != null && (
        <div className="chart-tip" style={{
          left: `${((hover + 0.5) / data.length) * 100}%`,
          // keep the tooltip inside the chart near either edge
          transform: `translate(${hover < data.length * 0.15 ? '-10%' : hover > data.length * 0.85 ? '-90%' : '-50%'}, -100%)`,
        }}>
          <strong className="mono">{data[hover].value}</strong> {unit}
          <span>{data[hover].tip || data[hover].label}</span>
        </div>
      )}
    </div>
  );
}

// Ranked horizontal bars with direct value labels. data: [{ name, count }]
export function Ranked({ data, limit = 8, format = (s) => s }) {
  const rows = data.slice(0, limit);
  const max = Math.max(1, ...rows.map((d) => d.count));
  if (!rows.length) return <p className="empty-line">No data for this period.</p>;
  return (
    <ul className="ranked">
      {rows.map((d) => (
        <li key={d.name} title={`${format(d.name)}: ${d.count}`}>
          <span className="ranked-name ellipsis">{format(d.name)}</span>
          <span className="ranked-track"><span className="ranked-bar" style={{ width: `${(d.count / max) * 100}%` }} /></span>
          <span className="ranked-val mono">{d.count}</span>
        </li>
      ))}
    </ul>
  );
}

function niceMax(v) {
  const p = 10 ** Math.floor(Math.log10(v));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((n) => n >= v) || v;
}

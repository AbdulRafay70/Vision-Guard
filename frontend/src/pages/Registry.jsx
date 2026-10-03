import { useMemo, useState } from 'react';
import { api } from '../lib/api';
import { inScope } from '../lib/registry';
import { locationOptions, placementKey } from '../lib/locations';
import { Plus, Trash2, Pin, PinOff, Power, RefreshCw, MonitorPlay, Building2, Map, Signpost } from '../components/Icons';

export default function Registry({ cameras, registry, pinned, togglePin, focusCamera, onRefresh, onNavigate }) {
  const [sel, setSel] = useState({});
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(null);

  const city = registry.cities.find((c) => c.id === sel.cityId);
  const area = city?.areas.find((a) => a.id === sel.areaId);
  const options = useMemo(() => locationOptions(registry.cities), [registry.cities]);

  const count = (scope) => cameras.filter((c) => inScope(c.placement, scope)).length;

  const rows = cameras.filter((c) => {
    if (sel.unassigned) return !c.placement;
    if (!inScope(c.placement, sel)) return false;
    const q = query.trim().toLowerCase();
    return !q || c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q) || c.source.toLowerCase().includes(q);
  });

  const disconnect = async (cam) => {
    if (!window.confirm(`Disconnect ${cam.name}? The stream will stop and the camera will be removed from the server.`)) return;
    setBusy(cam.id);
    try { await api.disconnectCamera(cam.id); registry.unplace(cam.id); } catch (e) { window.alert(e.message); }
    setBusy(null);
    onRefresh();
  };

  const remove = (level, ids, name) => {
    if (window.confirm(`Remove ${name}? Cameras placed here will become unassigned.`)) {
      registry.removeNode(level, ids);
      setSel(level === 'city' ? {} : level === 'area' ? { cityId: ids.cityId } : { cityId: ids.cityId, areaId: ids.areaId });
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Camera registry</h1>
          <p className="muted">Browse the network by city, area and street. Select a level to filter the camera list.</p>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={onRefresh}><RefreshCw size={15} /> Refresh</button>
        <button className="btn btn-primary" onClick={() => onNavigate('connect')}><Plus size={15} /> Connect camera</button>
      </div>

      <div className="miller panel">
        <Column
          icon={Building2} title="Cities"
          items={registry.cities.map((c) => ({ id: c.id, name: c.name, count: count({ cityId: c.id }) }))}
          selected={sel.cityId}
          onSelect={(id) => setSel({ cityId: id })}
          onAdd={(name) => setSel({ cityId: registry.addCity(name) })}
          onRemove={(it) => remove('city', { cityId: it.id }, it.name)}
          placeholder="New city"
          footer={<button className={`miller-item ${sel.unassigned ? 'is-selected' : ''}`} onClick={() => setSel({ unassigned: true })}><span>Unassigned cameras</span><span className="mono small">{cameras.filter((c) => !c.placement).length}</span></button>}
        />
        <Column
          icon={Map} title="Areas"
          items={(city?.areas || []).map((a) => ({ id: a.id, name: a.name, count: count({ cityId: city.id, areaId: a.id }) }))}
          selected={sel.areaId}
          disabled={!city}
          emptyText={city ? 'No areas yet.' : 'Select a city.'}
          onSelect={(id) => setSel({ cityId: city.id, areaId: id })}
          onAdd={(name) => setSel({ cityId: city.id, areaId: registry.addArea(city.id, name) })}
          onRemove={(it) => remove('area', { cityId: city.id, areaId: it.id }, it.name)}
          placeholder="New area"
        />
        <Column
          icon={Signpost} title="Streets"
          items={(area?.streets || []).map((s) => ({ id: s.id, name: s.name, count: count({ cityId: city.id, areaId: area.id, streetId: s.id }) }))}
          selected={sel.streetId}
          disabled={!area}
          emptyText={area ? 'No streets yet.' : 'Select an area.'}
          onSelect={(id) => setSel({ cityId: city.id, areaId: area.id, streetId: id })}
          onAdd={(name) => setSel({ cityId: city.id, areaId: area.id, streetId: registry.addStreet(city.id, area.id, name) })}
          onRemove={(it) => remove('street', { cityId: city.id, areaId: area.id, streetId: it.id }, it.name)}
          placeholder="New street"
        />
      </div>

      <section className="panel">
        <div className="panel-head">
          <h3>Cameras</h3>
          <span className="muted small">{rows.length} shown</span>
          <div className="spacer" />
          <input className="search" placeholder="Filter by name, ID or source" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr><th>#</th><th>Camera</th><th>Type</th><th>Location</th><th>Status</th><th className="num">FPS</th><th className="num">Latency</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id}>
                  <td className="mono muted">{String(cameras.indexOf(c) + 1).padStart(2, '0')}</td>
                  <td>
                    <strong>{c.name}</strong>
                    <div className="mono small muted ellipsis" title={c.source}>{c.id} · {c.source || '—'}</div>
                  </td>
                  <td className="upper small">{c.type}</td>
                  <td>
                    <select className="select-sm" value={placementKey(c.placement)} onChange={(e) => (e.target.value ? registry.place(c.id, JSON.parse(e.target.value)) : registry.unplace(c.id))}>
                      <option value="">Unassigned</option>
                      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </td>
                  <td><span className={`tag ${c.active ? 'tag-live' : 'tag-off'}`}>{c.active ? 'Streaming' : 'Offline'}</span></td>
                  <td className="num mono">{c.active ? Number(c.stats?.display_fps || 0).toFixed(1) : '—'}</td>
                  <td className="num mono">{c.active ? `${Math.round(c.stats?.avg_frame_age_ms || 0)} ms` : '—'}</td>
                  <td className="row-actions">
                    <button className="icon-btn" title="View live" onClick={() => focusCamera(c.id)}><MonitorPlay size={15} /></button>
                    <button className="icon-btn" title={pinned.includes(c.id) ? 'Remove from dashboard' : 'Pin to dashboard'} onClick={() => togglePin(c.id)}>
                      {pinned.includes(c.id) ? <PinOff size={15} /> : <Pin size={15} />}
                    </button>
                    <button className="icon-btn danger" title="Disconnect" disabled={busy === c.id} onClick={() => disconnect(c)}><Power size={15} /></button>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={8} className="empty-line">No cameras match this selection.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Column({ icon: Icon, title, items, selected, onSelect, onAdd, onRemove, placeholder, disabled, emptyText, footer }) {
  const [name, setName] = useState('');
  const add = (e) => { e.preventDefault(); if (name.trim()) { onAdd(name.trim()); setName(''); } };
  return (
    <div className={`miller-col ${disabled ? 'is-disabled' : ''}`}>
      <div className="miller-head"><Icon size={14} /><span>{title}</span></div>
      <div className="miller-list">
        {items.map((it) => (
          <div key={it.id} className={`miller-item ${selected === it.id ? 'is-selected' : ''}`}>
            <button onClick={() => onSelect(it.id)}><span>{it.name}</span><span className="mono small">{it.count}</span></button>
            <button className="miller-del" title={`Remove ${it.name}`} onClick={() => onRemove(it)}><Trash2 size={13} /></button>
          </div>
        ))}
        {items.length === 0 && <p className="empty-line">{emptyText}</p>}
        {footer}
      </div>
      {!disabled && (
        <form className="miller-add" onSubmit={add}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={placeholder} />
          <button className="icon-btn" title="Add"><Plus size={15} /></button>
        </form>
      )}
    </div>
  );
}

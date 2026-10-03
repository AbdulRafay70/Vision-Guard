import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import { inScope } from '../lib/registry';
import { can } from '../lib/roles';
import { locationOptions, placementKey } from '../lib/locations';
import Modal from '../components/Modal';
import { Plus, Trash2, Pin, PinOff, Power, Play, RefreshCw, MonitorPlay, Building2, Map, Signpost, Pencil, ShieldAlert } from '../components/Icons';
import AccessFields, { BASIS_TAG } from '../components/AccessFields';

const STATUS = {
  online: ['tag-live', 'Streaming'],
  connecting: ['tag-warn', 'Connecting'],
  error: ['tag-bad', 'Fault'],
  stopped: ['tag-off', 'Stopped'],
};

export default function Registry({ user, cameras, registry, pinned, togglePin, focusCamera, onRefresh, onNavigate, cameraAction, notify }) {
  const [sel, setSel] = useState({});
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState(null);
  const [editing, setEditing] = useState(null);
  const [accessCam, setAccessCam] = useState(null);
  const admin = can.manageCameras(user);
  const operator = can.operateCameras(user);

  const city = registry.cities.find((c) => c.id === sel.cityId);
  const area = city?.areas.find((a) => a.id === sel.areaId);
  const options = useMemo(() => locationOptions(registry.cities), [registry.cities]);
  const count = (scope) => cameras.filter((c) => inScope(c.placement, scope)).length;

  const rows = cameras.filter((c) => {
    if (sel.unassigned ? c.placement : !inScope(c.placement, sel)) return false;
    const q = query.trim().toLowerCase();
    return !q || c.name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q) || c.source.toLowerCase().includes(q);
  });

  const act = async (id, fn) => {
    setBusy(id);
    try { const msg = await fn(); if (msg) notify(msg); } catch (e) { notify(e.message, 'bad'); }
    setBusy(null);
  };

  const remove = (cam) => {
    if (!window.confirm(`Delete ${cam.name}? The stream stops and the camera is removed from the database.`)) return;
    act(cam.id, async () => { await api.deleteCamera(cam.id); await onRefresh(); await registry.reload(); return `${cam.name} deleted.`; });
  };

  const setLocation = (cam, value) => act(cam.id, async () => {
    if (value) await registry.place(cam.id, JSON.parse(value)); else await registry.unplace(cam.id);
    return `${cam.name} location saved.`;
  });

  const removeNode = (level, ids, name) => {
    if (!window.confirm(`Remove ${name}? Everything under it is deleted and its cameras become unassigned.`)) return;
    act(name, async () => {
      await registry.removeNode(level, ids);
      setSel(level === 'city' ? {} : level === 'area' ? { cityId: ids.cityId } : { cityId: ids.cityId, areaId: ids.areaId });
      return `${name} removed.`;
    });
  };

  const addNode = (fn) => async (name) => { try { await fn(name); } catch (e) { notify(e.message, 'bad'); } };

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Camera registry</h1>
          <p className="muted">Browse the network by city, area and street. Locations and cameras are stored in the command database.</p>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => { onRefresh(); registry.reload(); }}><RefreshCw size={15} /> Refresh</button>
        {admin && <button className="btn btn-primary" onClick={() => onNavigate('connect')}><Plus size={15} /> Connect camera</button>}
      </div>

      <div className="miller panel">
        <Column
          icon={Building2} title="Cities" canEdit={admin}
          items={registry.cities.map((c) => ({ id: c.id, name: c.name, count: count({ cityId: c.id }) }))}
          selected={sel.cityId}
          onSelect={(id) => setSel({ cityId: id })}
          onAdd={addNode(async (name) => setSel({ cityId: await registry.addCity(name) }))}
          onRename={(it, name) => act(it.id, async () => { await registry.rename('city', it.id, name); return 'City renamed.'; })}
          onRemove={(it) => removeNode('city', { cityId: it.id }, it.name)}
          placeholder="New city"
          footer={<button className={`miller-item miller-extra ${sel.unassigned ? 'is-selected' : ''}`} onClick={() => setSel({ unassigned: true })}><span>Unassigned cameras</span><span className="mono small">{cameras.filter((c) => !c.placement).length}</span></button>}
        />
        <Column
          icon={Map} title="Areas" canEdit={admin}
          items={(city?.areas || []).map((a) => ({ id: a.id, name: a.name, count: count({ cityId: city.id, areaId: a.id }) }))}
          selected={sel.areaId}
          disabled={!city}
          emptyText={city ? 'No areas yet.' : 'Select a city.'}
          onSelect={(id) => setSel({ cityId: city.id, areaId: id })}
          onAdd={addNode(async (name) => setSel({ cityId: city.id, areaId: await registry.addArea(city.id, name) }))}
          onRename={(it, name) => act(it.id, async () => { await registry.rename('area', it.id, name); return 'Area renamed.'; })}
          onRemove={(it) => removeNode('area', { cityId: city.id, areaId: it.id }, it.name)}
          placeholder="New area"
        />
        <Column
          icon={Signpost} title="Streets" canEdit={admin}
          items={(area?.streets || []).map((s) => ({ id: s.id, name: s.name, count: count({ cityId: city.id, areaId: area.id, streetId: s.id }) }))}
          selected={sel.streetId}
          disabled={!area}
          emptyText={area ? 'No streets yet.' : 'Select an area.'}
          onSelect={(id) => setSel({ cityId: city.id, areaId: area.id, streetId: id })}
          onAdd={addNode(async (name) => setSel({ cityId: city.id, areaId: area.id, streetId: await registry.addStreet(city.id, area.id, name) }))}
          onRename={(it, name) => act(it.id, async () => { await registry.rename('street', it.id, name); return 'Street renamed.'; })}
          onRemove={(it) => removeNode('street', { cityId: city.id, areaId: area.id, streetId: it.id }, it.name)}
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
              <tr><th>#</th><th>Camera</th><th>Type</th><th>Location</th><th>Access</th><th>Status</th><th className="num">FPS</th><th className="num">Latency</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((c) => {
                const [cls, label] = STATUS[c.status] || ['tag-off', c.status || 'Unknown'];
                return (
                  <tr key={c.id}>
                    <td className="mono muted">{String(cameras.indexOf(c) + 1).padStart(2, '0')}</td>
                    <td>
                      <strong>{c.name}</strong>
                      <div className="mono small muted ellipsis" title={c.source}>{c.id} · {c.source || '—'}</div>
                      {c.device && <div className="small muted">{c.device.device_name}{c.device.device_kind === 'dvr' ? ` · channel ${c.device.channel}` : ''}{c.link?.transport ? ` · ${c.link.transport.toUpperCase()}` : ''}</div>}
                    </td>
                    <td className="upper small">{c.type}</td>
                    <td>
                      <select className="select-sm" disabled={!admin || busy === c.id} value={placementKey(c.placement)} onChange={(e) => setLocation(c, e.target.value)}>
                        <option value="">Unassigned</option>
                        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    </td>
                    <td>
                      {c.access ? (
                        <span className={`tag ${c.access.revoked ? 'tag-bad' : BASIS_TAG[c.access.basis] || 'tag-off'}`} title={[c.access.basis_label, c.access.owner_name, c.access.reference].filter(Boolean).join(' · ')}>
                          {c.access.revoked ? 'Revoked' : c.access.basis_label}
                        </span>
                      ) : <span className="tag tag-warn" title="No lawful basis recorded">Unverified</span>}
                    </td>
                    <td>
                      <span className={`tag ${cls}`}>{label}</span>
                      {c.status !== 'online' && c.status_message && <div className="small muted ellipsis" title={c.status_message}>{c.status_message}</div>}
                    </td>
                    <td className="num mono">{c.active ? Number(c.stats?.display_fps || 0).toFixed(1) : '—'}</td>
                    <td className="num mono">{c.active ? `${Math.round(c.stats?.avg_frame_age_ms || 0)} ms` : '—'}</td>
                    <td className="row-actions">
                      <button className="icon-btn" title="View live" onClick={() => focusCamera(c.id)}><MonitorPlay size={15} /></button>
                      <button className="icon-btn" title={pinned.includes(c.id) ? 'Remove from dashboard' : 'Pin to dashboard'} onClick={() => togglePin(c.id)}>
                        {pinned.includes(c.id) ? <PinOff size={15} /> : <Pin size={15} />}
                      </button>
                      {operator && (c.enabled ? (
                        <button className="icon-btn" title="Stop stream" disabled={busy === c.id} onClick={() => act(c.id, () => cameraAction('stop', c.id))}><Power size={15} /></button>
                      ) : (
                        <button className="icon-btn" title="Start stream" disabled={busy === c.id} onClick={() => act(c.id, () => cameraAction('start', c.id))}><Play size={15} /></button>
                      ))}
                      {operator && c.enabled && c.status === 'error' && (
                        <button className="icon-btn" title="Retry now" disabled={busy === c.id} onClick={() => act(c.id, () => cameraAction('start', c.id))}><RefreshCw size={15} /></button>
                      )}
                      {admin && <button className="icon-btn" title="Access authorisation" onClick={() => setAccessCam(c)}><ShieldAlert size={15} /></button>}
                      {admin && <button className="icon-btn" title="Edit" onClick={() => setEditing(c)}><Pencil size={15} /></button>}
                      {admin && <button className="icon-btn danger" title="Delete" disabled={busy === c.id} onClick={() => remove(c)}><Trash2 size={15} /></button>}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && <tr><td colSpan={9} className="empty-line">No cameras match this selection.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      {editing && <EditCamera camera={editing} onClose={() => setEditing(null)} onSaved={async (msg) => { setEditing(null); notify(msg); await onRefresh(); }} />}
      {accessCam && <AccessModal camera={accessCam} onClose={() => setAccessCam(null)} onSaved={async (msg) => { setAccessCam(null); notify(msg); await onRefresh(); }} notify={notify} />}
    </div>
  );
}

function EditCamera({ camera, onClose, onSaved }) {
  const [form, setForm] = useState({ name: camera.name, type: camera.type, source: camera.source });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  // Load the unmasked source (admins only)
  useEffect(() => { api.camera(camera.id).then((c) => setForm((f) => ({ ...f, source: String(c.source) }))).catch(() => {}); }, [camera.id]);

  const save = async () => {
    setBusy(true); setError('');
    try {
      const res = await api.updateCamera(camera.id, form);
      await onSaved(`${res.name} saved${res.status === 'online' ? '' : ` — ${res.status_message || res.status}`}.`);
    } catch (e) { setError(e.message); setBusy(false); }
  };

  return (
    <Modal title={`Edit ${camera.name}`} onClose={onClose}
      footer={<><button className="btn btn-ghost" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy} onClick={save}>{busy ? 'Saving…' : 'Save'}</button></>}>
      <label className="field"><span>Display name</span><input value={form.name} onChange={set('name')} /></label>
      <label className="field"><span>Type</span>
        <select value={form.type} onChange={set('type')}>
          <option value="rtsp">IP camera (RTSP / HTTP)</option><option value="webcam">Local device</option><option value="video">Recorded video</option>
        </select>
      </label>
      <label className="field"><span>Source</span><input className="mono" value={form.source} onChange={set('source')} /></label>
      <p className="muted small">Changing the type or source restarts the stream.</p>
      {error && <div className="notice notice-error">{error}</div>}
    </Modal>
  );
}

function Column({ icon: Icon, title, items, selected, onSelect, onAdd, onRename, onRemove, placeholder, disabled, emptyText, footer, canEdit }) {
  const [name, setName] = useState('');
  const [renaming, setRenaming] = useState(null);
  const add = (e) => { e.preventDefault(); if (name.trim()) { onAdd(name.trim()); setName(''); } };
  return (
    <div className={`miller-col ${disabled ? 'is-disabled' : ''}`}>
      <div className="miller-head"><Icon size={14} /><span>{title}</span></div>
      <div className="miller-list">
        {items.map((it) => (
          <div key={it.id} className={`miller-item ${selected === it.id ? 'is-selected' : ''}`}>
            {renaming === it.id ? (
              <form className="miller-rename" onSubmit={(e) => { e.preventDefault(); const v = e.target.elements.n.value.trim(); if (v && v !== it.name) onRename(it, v); setRenaming(null); }}>
                <input name="n" defaultValue={it.name} autoFocus onBlur={() => setRenaming(null)} />
              </form>
            ) : (
              <button onClick={() => onSelect(it.id)} onDoubleClick={() => canEdit && setRenaming(it.id)}><span>{it.name}</span><span className="mono small">{it.count}</span></button>
            )}
            {canEdit && renaming !== it.id && <button className="miller-del" title={`Rename ${it.name}`} onClick={() => setRenaming(it.id)}><Pencil size={13} /></button>}
            {canEdit && renaming !== it.id && <button className="miller-del" title={`Remove ${it.name}`} onClick={() => onRemove(it)}><Trash2 size={13} /></button>}
          </div>
        ))}
        {items.length === 0 && <p className="empty-line">{emptyText}</p>}
        {footer}
      </div>
      {!disabled && canEdit && (
        <form className="miller-add" onSubmit={add}>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder={placeholder} />
          <button className="icon-btn" title="Add"><Plus size={15} /></button>
        </form>
      )}
    </div>
  );
}

function AccessModal({ camera, onClose, onSaved, notify }) {
  const [value, setValue] = useState({ basis: '' });
  const [loaded, setLoaded] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.cameraAccess(camera.id).then((g) => { setLoaded(g); if (g && g.basis) setValue(g); }).catch(() => {});
  }, [camera.id]);

  const save = async () => {
    setBusy(true);
    try { await api.setAccess(camera.id, value); await onSaved(`Access basis saved for ${camera.name}.`); } catch (e) { notify(e.message, 'bad'); setBusy(false); }
  };
  const revoke = async () => {
    if (!window.confirm(`Revoke access to ${camera.name}? The stream stops immediately and stays blocked until access is re-granted.`)) return;
    setBusy(true);
    try { await api.revokeAccess(camera.id); await onSaved(`Access to ${camera.name} revoked — stream blocked.`); } catch (e) { notify(e.message, 'bad'); setBusy(false); }
  };

  return (
    <Modal title={`Access authorisation · ${camera.name}`} onClose={onClose} wide
      footer={<>
        {loaded && loaded.basis && !loaded.revoked && <button className="btn btn-ghost danger" disabled={busy} onClick={revoke}>Revoke access</button>}
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={onClose}>Cancel</button>
        <button className="btn btn-primary" disabled={busy || !value.basis} onClick={save}>{loaded?.revoked ? 'Re-grant access' : 'Save'}</button>
      </>}>
      {loaded?.revoked && <div className="notice notice-error"><ShieldAlert size={16} />Access was revoked by {loaded.revoked_by} on {loaded.revoked_at}. Saving a basis re-grants access and allows the stream to resume.</div>}
      {loaded && loaded.granted_by && <p className="muted small">Recorded by {loaded.granted_by} on {loaded.granted_at}.</p>}
      <AccessFields value={value} onChange={setValue} />
    </Modal>
  );
}

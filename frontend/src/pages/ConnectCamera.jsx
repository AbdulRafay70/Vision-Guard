import { useState } from 'react';
import { api } from '../lib/api';
import { Check, CircleAlert, Upload, Radio } from '../components/Icons';

const TYPES = [
  { id: 'rtsp', label: 'IP camera (RTSP / HTTP)', hint: 'rtsp://user:pass@10.0.0.21:554/stream1' },
  { id: 'webcam', label: 'Local device', hint: 'Device index, e.g. 0' },
  { id: 'video', label: 'Recorded video', hint: 'Server path to a video file, or upload a clip' },
];

const NEW = '__new__';

export default function ConnectCamera({ registry, onConnected }) {
  const [cityId, setCityId] = useState(registry.cities[0]?.id || '');
  const [areaId, setAreaId] = useState('');
  const [streetId, setStreetId] = useState('');
  const [newName, setNewName] = useState({ city: '', area: '', street: '' });

  const [type, setType] = useState('rtsp');
  const [name, setName] = useState('');
  const [camId, setCamId] = useState('');
  const [source, setSource] = useState('');

  const [test, setTest] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState('');

  const city = registry.cities.find((c) => c.id === cityId);
  const area = city?.areas.find((a) => a.id === areaId);

  // Resolve "new …" selections into real registry nodes at submit time
  const resolveLocation = () => {
    let c = cityId, a = areaId, s = streetId;
    if (c === NEW) { if (!newName.city.trim()) throw new Error('Enter the new city name.'); c = registry.addCity(newName.city); }
    if (!c) throw new Error('Select a city.');
    if (a === NEW) { if (!newName.area.trim()) throw new Error('Enter the new area name.'); a = registry.addArea(c, newName.area); }
    if (!a) throw new Error('Select an area.');
    if (s === NEW) { if (!newName.street.trim()) throw new Error('Enter the new street name.'); s = registry.addStreet(c, a, newName.street); }
    return { cityId: c, areaId: a, ...(s ? { streetId: s } : {}) };
  };

  const areaName = () => (areaId === NEW ? newName.area : area?.name) || '';

  const runTest = async () => {
    setTest(null); setBusy('test');
    try { setTest(await api.testConnection(type, source)); } catch (e) { setTest({ status: 'offline', message: e.message }); }
    setBusy('');
  };

  const upload = async (file) => {
    if (!file) return;
    setBusy('upload'); setMsg(null);
    try {
      const res = await api.uploadVideo(file);
      setSource(res.path);
      if (!name) setName(file.name.replace(/\.[^.]+$/, ''));
      setMsg({ ok: true, text: `Uploaded ${file.name} (${(res.size_bytes / 1048576).toFixed(1)} MB).` });
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setBusy('');
  };

  const submit = async (e) => {
    e.preventDefault();
    setMsg(null);
    if (!name.trim()) { setMsg({ ok: false, text: 'Enter a camera name.' }); return; }
    if (!String(source).trim()) { setMsg({ ok: false, text: 'Enter the camera source.' }); return; }
    let placement;
    try { placement = resolveLocation(); } catch (err) { setMsg({ ok: false, text: err.message }); return; }

    setBusy('connect');
    try {
      const res = await api.connectCamera({
        id: camId.trim() || undefined,
        name: name.trim(),
        type,
        source: type === 'webcam' ? Number(source) : source.trim(),
        sector: areaName(),
      });
      registry.place(res.id, placement);
      onConnected(res.id);
      setMsg({ ok: true, text: `${res.name} is connected and streaming. It has been pinned to the dashboard.` });
      setName(''); setCamId(''); setSource(''); setTest(null);
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    }
    setBusy('');
  };

  const typeInfo = TYPES.find((t) => t.id === type);

  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Connect camera</h1>
          <p className="muted">Register a new feed. It starts streaming through the AI pipeline as soon as it connects; other feeds are not interrupted.</p>
        </div>
      </div>

      <form className="form-sections" onSubmit={submit}>
        <fieldset className="panel form-section">
          <legend><span className="step">1</span>Installation site</legend>
          <div className="form-grid three">
            <LevelSelect label="City" value={cityId} onChange={(v) => { setCityId(v); setAreaId(''); setStreetId(''); }}
              items={registry.cities} newLabel="New city…" newValue={newName.city} onNewValue={(v) => setNewName((n) => ({ ...n, city: v }))} required />
            <LevelSelect label="Area" value={areaId} onChange={(v) => { setAreaId(v); setStreetId(''); }} disabled={!cityId}
              items={city?.areas || []} newLabel="New area…" newValue={newName.area} onNewValue={(v) => setNewName((n) => ({ ...n, area: v }))} required />
            <LevelSelect label="Street" value={streetId} onChange={setStreetId} disabled={!areaId} optional
              items={area?.streets || []} newLabel="New street…" newValue={newName.street} onNewValue={(v) => setNewName((n) => ({ ...n, street: v }))} />
          </div>
        </fieldset>

        <fieldset className="panel form-section">
          <legend><span className="step">2</span>Camera</legend>
          <div className="form-grid two">
            <label className="field"><span>Display name</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Empress Market — North gate" /></label>
            <label className="field"><span>Camera ID <em>optional</em></span><input className="mono" value={camId} onChange={(e) => setCamId(e.target.value)} placeholder="Generated if left blank" /></label>
          </div>
          <div className="segmented">
            {TYPES.map((t) => (
              <button type="button" key={t.id} className={type === t.id ? 'is-active' : ''} onClick={() => { setType(t.id); setTest(null); }}>{t.label}</button>
            ))}
          </div>
          <label className="field">
            <span>Source</span>
            <input className="mono" value={source} onChange={(e) => setSource(e.target.value)} placeholder={typeInfo.hint} />
          </label>
          {type === 'video' && (
            <label className="upload">
              <Upload size={16} />
              <span>{busy === 'upload' ? 'Uploading…' : 'Upload a video clip to the server'}</span>
              <input type="file" accept="video/*" onChange={(e) => upload(e.target.files?.[0])} hidden />
            </label>
          )}
        </fieldset>

        <fieldset className="panel form-section">
          <legend><span className="step">3</span>Verify and connect</legend>
          <div className="form-actions">
            <button type="button" className="btn btn-ghost" disabled={!source || busy} onClick={runTest}>
              <Radio size={15} /> {busy === 'test' ? 'Testing…' : 'Test connection'}
            </button>
            {test && (
              <span className={`test-result tone-${test.status === 'online' ? 'ok' : 'bad'}`}>
                <i className={`dot dot-${test.status === 'online' ? 'ok' : 'bad'}`} />
                {test.message}{test.latency_ms != null && <span className="mono muted"> · {test.latency_ms} ms</span>}
              </span>
            )}
            <div className="spacer" />
            <button className="btn btn-primary" disabled={!!busy}>{busy === 'connect' ? 'Connecting…' : 'Connect camera'}</button>
          </div>
          {msg && <div className={`notice ${msg.ok ? 'notice-ok' : 'notice-error'}`}>{msg.ok ? <Check size={16} /> : <CircleAlert size={16} />}{msg.text}</div>}
        </fieldset>
      </form>
    </div>
  );
}

function LevelSelect({ label, value, onChange, items, newLabel, newValue, onNewValue, disabled, optional }) {
  return (
    <label className="field">
      <span>{label} {optional && <em>optional</em>}</span>
      <select value={value} onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        <option value="">{optional ? '— None —' : `Select ${label.toLowerCase()}`}</option>
        {items.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
        <option value={NEW}>{newLabel}</option>
      </select>
      {value === NEW && <input className="field-sub" autoFocus value={newValue} onChange={(e) => onNewValue(e.target.value)} placeholder={`${label} name`} />}
    </label>
  );
}

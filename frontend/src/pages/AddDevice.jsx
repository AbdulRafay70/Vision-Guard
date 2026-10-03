import { useEffect, useMemo, useState } from 'react';
import { api } from '../lib/api';
import { ManualConnect, LevelSelect, NEW } from './ConnectCamera';
import { Check, CircleAlert, Radio, Search, Trash2, RefreshCw } from '../components/Icons';
import AccessFields from '../components/AccessFields';

const STEPS = ['Checking network ports', 'Asking the device over ONVIF', 'Trying stream paths', 'Grabbing a live frame from each stream'];

export default function ConnectCamera(props) {
  const [tab, setTab] = useState('device');
  return (
    <div className="page page-narrow">
      <div className="page-head">
        <div>
          <h1>Connect camera</h1>
          <p className="muted">Add a standalone IP / WiFi camera or a whole DVR / NVR in one step. Enter its address and login — VisionGuard finds the stream URLs, verifies each channel with a live frame, and starts them.</p>
        </div>
      </div>
      <div className="segmented">
        <button className={tab === 'device' ? 'is-active' : ''} onClick={() => setTab('device')}>Camera or DVR / NVR (auto-detect)</button>
        <button className={tab === 'manual' ? 'is-active' : ''} onClick={() => setTab('manual')}>Stream URL, local device or video file</button>
      </div>
      {tab === 'device' ? <DeviceWizard {...props} /> : <ManualConnect {...props} />}
      <DeviceList {...props} />
    </div>
  );
}

function DeviceWizard({ registry, onConnected, notify }) {
  const [brands, setBrands] = useState([]);
  const [form, setForm] = useState({ kind: 'camera', brand: 'auto', ip: '', username: 'admin', password: '', rtsp_port: '', http_port: '', max_channels: 16, sub_stream: false });
  const [advanced, setAdvanced] = useState(false);
  const [scan, setScan] = useState(null); // null | 'busy' | [devices]
  const [probe, setProbe] = useState(null);
  const [busy, setBusy] = useState('');
  const [step, setStep] = useState(0);
  const [picked, setPicked] = useState({});
  const [names, setNames] = useState({});
  const [devName, setDevName] = useState('');
  const [loc, setLoc] = useState({ cityId: '', areaId: '', streetId: '' });
  const [access, setAccess] = useState({ basis: '' });
  const [newName, setNewName] = useState({ city: '', area: '', street: '' });
  const [result, setResult] = useState(null);

  useEffect(() => { api.deviceBrands().then(setBrands).catch(() => {}); }, []);
  useEffect(() => { if (!loc.cityId && registry.cities[0]) setLoc((l) => ({ ...l, cityId: registry.cities[0].id })); }, [loc.cityId, registry.cities]);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }));
  const city = registry.cities.find((c) => c.id === loc.cityId);
  const area = city?.areas.find((a) => a.id === loc.areaId);

  const runScan = async () => {
    setScan('busy');
    try { const r = await api.discoverDevices(); setScan(r.devices); } catch (e) { notify(e.message, 'bad'); setScan(null); }
  };

  const detect = async (e) => {
    e?.preventDefault();
    if (!form.ip.trim()) { notify('Enter the device IP address.', 'bad'); return; }
    setBusy('probe'); setProbe(null); setResult(null); setStep(0);
    const ticker = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 2500);
    try {
      const r = await api.probeDevice({
        ...form, ip: form.ip.trim(), rtsp_port: Number(form.rtsp_port) || 0, http_port: Number(form.http_port) || 0,
        max_channels: Number(form.max_channels) || 16,
      });
      setProbe(r);
      setPicked(Object.fromEntries(r.streams.map((s) => [s.channel, s.verified !== false])));
      setNames({});
      const label = [r.manufacturer, r.model].filter(Boolean).join(' ');
      setDevName(form.kind === 'dvr' ? `${label || 'DVR'} ${form.ip.trim()}` : `${label || 'Camera'} ${form.ip.trim()}`);
    } catch (err) { notify(err.message, 'bad'); }
    clearInterval(ticker);
    setBusy('');
  };

  const chosen = (probe?.streams || []).filter((s) => picked[s.channel]);

  const add = async () => {
    if (!chosen.length) { notify('Select at least one channel.', 'bad'); return; }
    if (!loc.cityId || !loc.areaId) { notify('Choose the city and area where the device is installed.', 'bad'); return; }
    if (!access.basis) { notify('Record the lawful basis for accessing this device.', 'bad'); return; }
    setBusy('add');
    try {
      // Create any new locations first
      const c = loc.cityId === NEW ? await registry.addCity(newName.city) : loc.cityId;
      const a = loc.areaId === NEW ? await registry.addArea(c, newName.area) : loc.areaId;
      const s = loc.streetId === NEW ? await registry.addStreet(c, a, newName.street) : loc.streetId;
      const res = await api.addDevice({
        device: { name: devName, kind: form.kind, brand: probe.brand, model: probe.model, ip: form.ip.trim(), username: form.username },
        streams: chosen.map((st) => ({ channel: st.channel, url: st.url, name: names[st.channel] || undefined })),
        location: { cityId: c, areaId: a, ...(s ? { streetId: s } : {}) },
        access,
      });
      await registry.reload();
      res.cameras.forEach((cam) => onConnected(cam.id));
      setResult(res);
      notify(`${res.online} of ${res.cameras.length} camera(s) online and pinned to the dashboard.`, res.online ? 'ok' : 'bad');
    } catch (err) { notify(err.message, 'bad'); }
    setBusy('');
  };

  return (
    <div className="form-sections">
      <form className="panel form-section" onSubmit={detect}>
        <legend className="legend"><span className="step">1</span>Device</legend>
        <div className="segmented">
          <button type="button" className={form.kind === 'camera' ? 'is-active' : ''} onClick={() => setForm((f) => ({ ...f, kind: 'camera' }))}>Standalone IP / WiFi camera</button>
          <button type="button" className={form.kind === 'dvr' ? 'is-active' : ''} onClick={() => setForm((f) => ({ ...f, kind: 'dvr' }))}>DVR / NVR recorder</button>
        </div>
        <div className="form-grid two">
          <label className="field"><span>IP address</span>
            <div className="input-row">
              <input className="mono" value={form.ip} onChange={set('ip')} placeholder="192.168.1.64" autoFocus />
              <button type="button" className="btn btn-ghost" onClick={runScan} disabled={scan === 'busy'} title="Find cameras and recorders on this network">
                <Search size={15} /> {scan === 'busy' ? 'Scanning…' : 'Scan'}
              </button>
            </div>
          </label>
          <label className="field"><span>Brand</span>
            <select value={form.brand} onChange={set('brand')}>
              <option value="auto">Auto-detect</option>
              {brands.map((b) => <option key={b.id} value={b.id}>{b.label}</option>)}
            </select>
          </label>
          <label className="field"><span>Username</span><input value={form.username} onChange={set('username')} autoComplete="off" /></label>
          <label className="field"><span>Password</span><input type="password" value={form.password} onChange={set('password')} autoComplete="new-password" placeholder={form.brand === 'ezviz' ? 'Verification code on the label' : ''} /></label>
        </div>

        {Array.isArray(scan) && (
          <div className="scan-results">
            {scan.length === 0 ? <p className="muted small">No cameras answered on this network. The server must be on the same LAN / VLAN as the devices.</p> : (
              <table className="table">
                <thead><tr><th>Address</th><th>Brand guess</th><th>ONVIF</th><th>Open ports</th><th /></tr></thead>
                <tbody>
                  {scan.map((d) => (
                    <tr key={d.ip}>
                      <td className="mono">{d.ip}</td>
                      <td className="cap">{d.brand || '—'}</td>
                      <td>{d.onvif ? 'Yes' : '—'}</td>
                      <td className="mono small muted">{d.ports.join(', ') || '—'}</td>
                      <td className="row-actions">{d.added ? <span className="muted small">Already added</span> : (
                        <button type="button" className="btn btn-ghost btn-sm" onClick={() => { setForm((f) => ({ ...f, ip: d.ip, brand: d.brand || 'auto' })); setScan(null); }}>Use</button>
                      )}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <button type="button" className="link" onClick={() => setAdvanced((v) => !v)}>{advanced ? 'Hide' : 'Show'} advanced options</button>
        {advanced && (
          <div className="form-grid three">
            <label className="field"><span>RTSP port <em>auto</em></span><input className="mono" value={form.rtsp_port} onChange={set('rtsp_port')} placeholder="554" /></label>
            <label className="field"><span>ONVIF / HTTP port <em>auto</em></span><input className="mono" value={form.http_port} onChange={set('http_port')} placeholder="80" /></label>
            {form.kind === 'dvr' && <label className="field"><span>Channels to check</span><input className="mono" value={form.max_channels} onChange={set('max_channels')} /></label>}
            <label className="check check-sm"><input type="checkbox" checked={form.sub_stream} onChange={set('sub_stream')} /><span className="small">Use sub-stream (lower bandwidth — good for WiFi and many channels)</span></label>
          </div>
        )}

        <div className="form-actions">
          <button className="btn btn-primary" disabled={busy === 'probe'}><Radio size={15} /> {busy === 'probe' ? 'Detecting…' : form.kind === 'dvr' ? 'Detect all channels' : 'Detect camera'}</button>
          {busy === 'probe' && <span className="muted small progress-step"><i className="spinner" />{STEPS[step]}…</span>}
        </div>
      </form>

      {probe && (
        <section className="panel form-section">
          <legend className="legend"><span className="step">2</span>Detected streams</legend>
          <div className="probe-summary">
            <span><span className="label">Device</span> {[probe.manufacturer, probe.model].filter(Boolean).join(' ') || '—'}</span>
            <span><span className="label">Brand</span> <span className="cap">{probe.brand || 'unknown'}</span></span>
            <span><span className="label">ONVIF</span> {probe.onvif ? 'Yes' : 'No'}</span>
            <span><span className="label">Ports</span> <span className="mono">{probe.open_ports.join(', ') || '—'}</span></span>
          </div>
          {probe.messages.map((m) => (
            <div key={m} className={`notice ${probe.streams.length ? 'notice-ok' : 'notice-error'}`}>{probe.streams.length ? <Check size={16} /> : <CircleAlert size={16} />}{m}</div>
          ))}
          {probe.streams.length > 0 && (
            <>
              <div className="channel-tools">
                <button type="button" className="link" onClick={() => setPicked(Object.fromEntries(probe.streams.map((s) => [s.channel, true])))}>Select all</button>
                <button type="button" className="link" onClick={() => setPicked({})}>Select none</button>
                <span className="muted small">{chosen.length} of {probe.streams.length} selected</span>
              </div>
              <div className="channel-grid">
                {probe.streams.map((s) => (
                  <label key={s.channel} className={`channel ${picked[s.channel] ? 'is-picked' : ''}`}>
                    <div className="channel-shot">
                      {s.snapshot ? <img src={`data:image/jpeg;base64,${s.snapshot}`} alt={`Channel ${s.channel}`} /> : <span>{s.verified === false ? 'No video' : 'Not verified'}</span>}
                      <span className={`tag ${s.verified ? 'tag-live' : s.verified === false ? 'tag-bad' : 'tag-off'}`}>{s.verified ? 'Verified' : s.verified === false ? 'No frames' : 'Unchecked'}</span>
                    </div>
                    <div className="channel-body">
                      <div className="channel-top">
                        <input type="checkbox" checked={!!picked[s.channel]} onChange={(e) => setPicked((p) => ({ ...p, [s.channel]: e.target.checked }))} />
                        <strong>CH {String(s.channel).padStart(2, '0')}</strong>
                        {s.width && <span className="mono small muted">{s.width}×{s.height}{s.fps ? ` · ${s.fps} fps` : ''}</span>}
                      </div>
                      <input className="input-sm" value={names[s.channel] ?? ''} placeholder={form.kind === 'dvr' ? `${devName} · CH${String(s.channel).padStart(2, '0')}` : devName}
                        onChange={(e) => setNames((n) => ({ ...n, [s.channel]: e.target.value }))} />
                      <span className="mono small muted ellipsis" title={s.url_masked}>{s.via} · {s.url_masked}</span>
                      {s.error && <span className="small tone-bad">{s.error}</span>}
                    </div>
                  </label>
                ))}
              </div>
            </>
          )}
        </section>
      )}

      {probe?.streams.length > 0 && (
        <section className="panel form-section">
          <legend className="legend"><span className="step">3</span>Name, location and add</legend>
          <label className="field"><span>{form.kind === 'dvr' ? 'Recorder name' : 'Camera name'}</span><input value={devName} onChange={(e) => setDevName(e.target.value)} /></label>
          <div className="form-grid three">
            <LevelSelect label="City" value={loc.cityId} onChange={(v) => setLoc({ cityId: v, areaId: '', streetId: '' })} items={registry.cities}
              newLabel="New city…" newValue={newName.city} onNewValue={(v) => setNewName((n) => ({ ...n, city: v }))} />
            <LevelSelect label="Area" value={loc.areaId} onChange={(v) => setLoc((l) => ({ ...l, areaId: v, streetId: '' }))} disabled={!loc.cityId} items={city?.areas || []}
              newLabel="New area…" newValue={newName.area} onNewValue={(v) => setNewName((n) => ({ ...n, area: v }))} />
            <LevelSelect label="Street" value={loc.streetId} onChange={(v) => setLoc((l) => ({ ...l, streetId: v }))} disabled={!loc.areaId} optional items={area?.streets || []}
              newLabel="New street…" newValue={newName.street} onNewValue={(v) => setNewName((n) => ({ ...n, street: v }))} />
          </div>
          <div className="access-block"><AccessFields value={access} onChange={setAccess} /></div>
          <div className="form-actions">
            <div className="spacer" />
            <button className="btn btn-primary" disabled={busy === 'add' || !chosen.length} onClick={add}>
              {busy === 'add' ? 'Connecting…' : `Add ${chosen.length} camera${chosen.length === 1 ? '' : 's'}`}
            </button>
          </div>
          {result && (
            <div className={`notice ${result.online === result.cameras.length ? 'notice-ok' : 'notice-error'}`}>
              {result.online === result.cameras.length ? <Check size={16} /> : <CircleAlert size={16} />}
              <span>
                {result.online} of {result.cameras.length} online.
                {result.cameras.filter((c) => c.status !== 'online').map((c) => <span key={c.id}><br />{c.name}: {c.status_message || c.status} — retrying automatically.</span>)}
              </span>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function DeviceList({ notify, onRefresh, registry }) {
  const [devices, setDevices] = useState([]);
  const load = () => api.devices().then(setDevices).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, []);
  const total = useMemo(() => devices.reduce((n, d) => n + d.cameras.length, 0), [devices]);

  const remove = async (d) => {
    if (!window.confirm(`Remove ${d.name} and its ${d.cameras.length} camera(s)?`)) return;
    try { await api.deleteDevice(d.id); notify(`${d.name} removed.`); load(); onRefresh(); registry.reload(); } catch (e) { notify(e.message, 'bad'); }
  };

  if (!devices.length) return null;
  return (
    <section className="panel">
      <div className="panel-head"><h3>Connected devices</h3><span className="muted small">{devices.length} devices · {total} channels</span><div className="spacer" /><button className="icon-btn" title="Refresh" onClick={load}><RefreshCw size={14} /></button></div>
      <table className="table">
        <thead><tr><th>Device</th><th>Type</th><th>Address</th><th className="num">Channels</th><th /></tr></thead>
        <tbody>
          {devices.map((d) => (
            <tr key={d.id}>
              <td><strong>{d.name}</strong><div className="small muted cap">{[d.brand, d.model].filter(Boolean).join(' · ')}</div></td>
              <td>{d.kind === 'dvr' ? 'DVR / NVR' : 'Camera'}</td>
              <td className="mono">{d.ip}</td>
              <td className="num mono">{d.cameras.length}</td>
              <td className="row-actions"><button className="icon-btn danger" title="Remove device and its cameras" onClick={() => remove(d)}><Trash2 size={15} /></button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

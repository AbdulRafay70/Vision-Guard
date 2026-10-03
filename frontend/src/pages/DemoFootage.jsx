import { useCallback, useEffect, useState } from 'react';
import { api, mediaUrl } from '../lib/api';
import { can } from '../lib/roles';
import { Play, Trash2, RefreshCw, Upload } from '../components/Icons';

const mb = (n) => `${(n / 1048576).toFixed(1)} MB`;

export default function DemoFootage({ user, registry, onRefresh, onDeployed, notify }) {
  const [videos, setVideos] = useState([]);
  const [picked, setPicked] = useState({}); // key -> { name, areaId, on }
  const [busy, setBusy] = useState('');
  const admin = can.manageCameras(user);
  const areas = registry.cities.flatMap((c) => c.areas.map((a) => ({ id: a.id, label: `${c.name} / ${a.name}`, name: a.name })));

  const key = (v) => `${v.folder}/${v.filename}`;
  const load = useCallback(() => api.demoVideos().then(setVideos).catch((e) => notify(e.message, 'bad')), [notify]);
  useEffect(() => { load(); }, [load]);

  const field = (v, k, fallback) => picked[key(v)]?.[k] ?? fallback;
  const set = (v, k, val) => setPicked((p) => ({ ...p, [key(v)]: { ...p[key(v)], [k]: val } }));
  const areaIdFor = (v) => field(v, 'areaId', areas.find((a) => a.name.toLowerCase() === v.suggested_area.toLowerCase())?.id || '');

  const deploy = async (list) => {
    setBusy('deploy');
    try {
      const res = await api.deployDemo(list.map((v) => ({
        folder: v.folder, filename: v.filename, name: field(v, 'name', v.suggested_name), areaId: areaIdFor(v) || undefined,
      })));
      const live = res.deployed.filter((d) => d.active);
      onDeployed(res.deployed.map((d) => d.id));
      await Promise.all([onRefresh(), registry.reload(), load()]);
      notify(live.length === res.deployed.length
        ? `${live.length} demo stream${live.length === 1 ? '' : 's'} live and pinned to the dashboard.`
        : `${live.length} of ${res.deployed.length} streams started — check the registry for faults.`, live.length ? 'ok' : 'bad');
    } catch (e) { notify(e.message, 'bad'); }
    setBusy('');
  };

  const clear = async () => {
    if (!window.confirm('Stop and remove every camera that streams a sample clip?')) return;
    setBusy('clear');
    try { const r = await api.clearDemo(); await Promise.all([onRefresh(), registry.reload(), load()]); notify(`${r.removed.length} demo camera(s) removed.`); } catch (e) { notify(e.message, 'bad'); }
    setBusy('');
  };

  const selected = videos.filter((v) => field(v, 'on', false));

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Demo footage</h1>
          <p className="muted">Recorded sample clips streamed as live, looping cameras through the full AI pipeline — for demonstrations and testing detection without field cameras.</p>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost btn-sm" onClick={load}><RefreshCw size={14} /> Refresh</button>
        {admin && <button className="btn btn-ghost btn-sm" onClick={clear} disabled={!!busy}><Trash2 size={14} /> Remove demo cameras</button>}
        {admin && <button className="btn btn-ghost" disabled={!!busy || !selected.length} onClick={() => deploy(selected)}><Play size={15} /> Stream selected ({selected.length})</button>}
        {admin && <button className="btn btn-primary" disabled={!!busy || !videos.length} onClick={() => deploy(videos)}><Play size={15} /> {busy === 'deploy' ? 'Starting…' : 'Stream all'}</button>}
      </div>

      {videos.length === 0 && (
        <div className="panel empty-state">
          <Upload size={20} />
          <p>No sample clips found.</p>
          <p className="muted small">Place .mp4 files in <span className="mono">prototype/Videos</span>, or upload a clip on the Connect camera page.</p>
        </div>
      )}

      <div className="demo-grid">
        {videos.map((v) => (
          <article key={key(v)} className={`panel demo-card ${field(v, 'on', false) ? 'is-picked' : ''}`}>
            <div className="demo-video">
              <video src={mediaUrl(v.preview_url)} muted loop autoPlay playsInline preload="metadata" />
              <span className={`tag ${v.streaming ? 'tag-live' : 'tag-off'}`}>{v.streaming ? 'Streaming' : v.registered ? 'Stopped' : 'Not deployed'}</span>
            </div>
            <div className="demo-body">
              {admin && (
                <label className="check check-sm">
                  <input type="checkbox" checked={field(v, 'on', false)} onChange={(e) => set(v, 'on', e.target.checked)} />
                  <span className="mono small muted ellipsis" title={v.filename}>{v.filename} · {mb(v.size_bytes)}{v.folder === 'uploads' ? ' · uploaded' : ''}</span>
                </label>
              )}
              <label className="field"><span>Camera name</span>
                <input value={field(v, 'name', v.suggested_name)} onChange={(e) => set(v, 'name', e.target.value)} disabled={!admin} />
              </label>
              <label className="field"><span>Shown in area</span>
                <select value={areaIdFor(v)} onChange={(e) => set(v, 'areaId', e.target.value)} disabled={!admin}>
                  <option value="">{v.suggested_area} (create)</option>
                  {areas.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              </label>
              {admin && <button className="btn btn-ghost btn-sm" disabled={!!busy} onClick={() => deploy([v])}><Play size={14} /> {v.streaming ? 'Restart / update' : 'Stream this clip'}</button>}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

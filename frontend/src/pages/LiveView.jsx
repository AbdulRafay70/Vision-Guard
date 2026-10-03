import { useMemo, useState } from 'react';
import CameraTile from '../components/CameraTile';
import LocationTree from '../components/LocationTree';
import { inScope } from '../lib/registry';
import { locationLabel, scopeLabel } from '../lib/cameras';
import { Square, Grid2x2, Grid3x3, LayoutGrid, ZoomIn, ZoomOut, Maximize2, Minimize2, ChevronRight } from '../components/Icons';

const LAYOUTS = [
  { size: 1, icon: Square, label: '1×1' },
  { size: 4, icon: Grid2x2, label: '2×2' },
  { size: 9, icon: Grid3x3, label: '3×3' },
  { size: 16, icon: LayoutGrid, label: '4×4' },
];

export default function LiveView({ cameras, registry, pinned, togglePin, focusCamera, view }) {
  const { scope, setScope, focusId, setFocusId, layout, setLayout, zoom, setZoom, theater, setTheater } = view;
  // Paging resets whenever the scope or layout changes
  const pageKey = `${JSON.stringify(scope)}|${layout}|${focusId}`;
  const [paging, setPaging] = useState({ key: pageKey, idx: 0 });
  const pageIdx = paging.key === pageKey ? paging.idx : 0;
  const setPageIdx = (idx) => setPaging({ key: pageKey, idx });

  const visible = useMemo(() => cameras.filter((c) => inScope(c.placement, scope)), [cameras, scope]);
  const focused = focusId ? cameras.find((c) => c.id === focusId) : null;

  // Single view shows the focused camera, else the first in scope
  const list = layout === 1 && focused ? [focused] : visible;
  const pages = Math.max(1, Math.ceil(list.length / layout));
  const page = Math.min(pageIdx, pages - 1);

  const slots = Array.from({ length: layout }, (_, i) => list[page * layout + i] || null);
  const cols = Math.sqrt(layout);

  return (
    <div className={`live ${theater ? 'is-theater' : ''}`}>
      <aside className="live-side panel">
        <div className="panel-head"><h3>Locations</h3></div>
        <LocationTree cities={registry.cities} cameras={cameras} scope={scope} onSelect={(s) => { setScope(s); setFocusId(null); if (layout === 1) setLayout(4); }} />
        <div className="panel-head"><h3>Cameras in view</h3><span className="muted mono small">{visible.length}</span></div>
        <ul className="cam-list">
          {visible.map((c) => (
            <li key={c.id}>
              <button className={focusId === c.id ? 'is-selected' : ''} onClick={() => focusCamera(c.id)}>
                <i className={`dot ${c.active ? 'dot-ok' : 'dot-off'}`} />
                <span className="mono small muted">{String(cameras.indexOf(c) + 1).padStart(2, "0")}</span>
                <span className="ellipsis">{c.name}</span>
              </button>
            </li>
          ))}
          {visible.length === 0 && <li className="empty-line">No cameras at this location.</li>}
        </ul>
      </aside>

      <section className="live-stage">
        <div className="toolbar">
          <div className="crumbs">
            <span>{scopeLabel(registry.cities, scope)}</span>
            {focused && layout === 1 && <><ChevronRight size={13} /><strong>{focused.name}</strong></>}
          </div>
          <div className="toolbar-group">
            {LAYOUTS.map(({ size, icon: Icon, label }) => (
              <button key={size} className={`icon-btn ${layout === size ? 'is-active' : ''}`} title={label} onClick={() => { setLayout(size); if (size > 1) setFocusId(null); }}>
                <Icon size={15} />
              </button>
            ))}
          </div>
          <div className="toolbar-group">
            <button className="icon-btn" title="Zoom out" onClick={() => setZoom((z) => Math.max(1, z - 0.5))} disabled={zoom <= 1}><ZoomOut size={15} /></button>
            <span className="mono small zoom-read">{zoom.toFixed(1)}×</span>
            <button className="icon-btn" title="Zoom in" onClick={() => setZoom((z) => Math.min(4, z + 0.5))}><ZoomIn size={15} /></button>
            <button className="icon-btn" title={theater ? 'Exit full screen (Esc)' : 'Full screen'} onClick={() => setTheater(!theater)}>
              {theater ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
          </div>
          {pages > 1 && (
            <div className="toolbar-group">
              <button className="btn btn-ghost btn-sm" disabled={page === 0} onClick={() => setPageIdx(page - 1)}>Prev</button>
              <span className="mono small">{page + 1}/{pages}</span>
              <button className="btn btn-ghost btn-sm" disabled={page >= pages - 1} onClick={() => setPageIdx(page + 1)}>Next</button>
            </div>
          )}
        </div>

        <div className="wall" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)`, gridTemplateRows: `repeat(${cols}, 1fr)` }}>
          {slots.map((cam, i) => (
            <CameraTile
              key={cam ? cam.id : `empty-${i}`}
              camera={cam}
              index={cam ? cameras.indexOf(cam) + 1 : null}
              location={cam && locationLabel(registry.cities, cam.placement)}
              zoom={zoom}
              compact={layout >= 16}
              pinned={cam && pinned.includes(cam.id)}
              onTogglePin={togglePin}
              onFocus={layout === 1 ? null : focusCamera}
            />
          ))}
        </div>
      </section>
    </div>
  );
}

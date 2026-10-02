import { useState } from 'react';
import { feedUrl } from '../lib/api';
import { Pin, PinOff, Maximize2 } from './Icons';

export default function CameraTile({ camera, location, index, zoom = 1, pinned, onTogglePin, onFocus, compact, highlight }) {
  const [failed, setFailed] = useState(false);

  if (!camera) {
    return <div className="tile tile-empty"><span>Empty slot</span></div>;
  }

  const live = camera.active && !failed;
  const fps = camera.stats?.display_fps;

  return (
    <div className={`tile ${highlight ? 'is-alert' : ''}`} onDoubleClick={() => onFocus?.(camera.id)}>
      <div className="tile-video">
        {live ? (
          <img
            src={feedUrl(camera.id)}
            alt={camera.name}
            style={{ transform: `scale(${zoom})` }}
            onError={() => setFailed(true)}
          />
        ) : (
          <div className="no-signal"><span>No signal</span><small>{camera.active ? 'Stream interrupted' : 'Camera offline'}</small></div>
        )}
      </div>
      <div className="tile-head">
        {index != null && <span className="tile-index mono">{String(index).padStart(2, '0')}</span>}
        <span className="tile-name">{camera.name}</span>
        <span className={`tag ${live ? 'tag-live' : 'tag-off'}`}>{live ? 'Live' : 'Off'}</span>
      </div>
      {!compact && (
        <div className="tile-foot">
          <span className="tile-loc">{location || 'Unassigned location'}</span>
          {live && fps != null && <span className="mono">{Number(fps).toFixed(0)} fps</span>}
        </div>
      )}
      <div className="tile-actions">
        {onTogglePin && (
          <button title={pinned ? 'Remove from dashboard' : 'Pin to dashboard'} onClick={() => onTogglePin(camera.id)}>
            {pinned ? <PinOff size={14} /> : <Pin size={14} />}
          </button>
        )}
        {onFocus && <button title="Open in single view" onClick={() => onFocus(camera.id)}><Maximize2 size={14} /></button>}
      </div>
    </div>
  );
}

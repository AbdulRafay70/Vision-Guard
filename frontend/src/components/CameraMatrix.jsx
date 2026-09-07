import React, { useState } from 'react';
import { 
  Camera, 
  Grid2X2, 
  Square, 
  LayoutGrid, 
  RefreshCw, 
  Download, 
  Maximize2,
  AlertCircle, 
  Radio, 
  Plus, 
  MapPin, 
  Navigation, 
  Layers,
  ShieldCheck,
  Video
} from 'lucide-react';

export default function CameraMatrix({ 
  cameras = [], 
  selectedCamId, 
  onSelectCam, 
  activeAlertCamId, 
  isBackendOnline = true, 
  areas = [], 
  onOpenConfigModal, 
  currentScope, 
  onOpenScopeSelector, 
  layout: parentLayout, 
  onLayoutChange 
}) {
  const [internalLayout, setInternalLayout] = useState('grid4'); // 'grid4' | 'solo' | 'grid8'
  const layout = parentLayout || internalLayout;
  const setLayout = (newLayout) => {
    if (onLayoutChange) onLayoutChange(newLayout);
    setInternalLayout(newLayout);
  };
  const [imgErrors, setImgErrors] = useState({});

  const handleImgError = (camId) => {
    setImgErrors(prev => ({ ...prev, [camId]: true }));
  };

  const handleRetry = (camId) => {
    setImgErrors(prev => ({ ...prev, [camId]: false }));
  };

  const defaultCameras = cameras;

  let displayCameras = defaultCameras;
  if (layout === 'solo') {
    displayCameras = defaultCameras.filter(c => c.id === selectedCamId || (defaultCameras.length > 0 && c.id === defaultCameras[0]?.id));
    if (displayCameras.length === 0 && defaultCameras.length > 0) displayCameras = [defaultCameras[0]];
  } else if (layout === 'grid4') {
    displayCameras = defaultCameras.slice(0, 4);
  } else if (layout === 'grid8') {
    displayCameras = defaultCameras.slice(0, 8);
  }

  return (
    <div className="camera-matrix-wrapper exec-card">
      {/* Executive Clean Toolbar */}
      <div className="matrix-toolbar">
        {/* Left: Brand Identity & Active Sector */}
        <div className="matrix-title-group">
          <div className="matrix-icon-pill">
            <Video size={16} className="text-indigo" />
            <span className="matrix-title">CCTV SURVEILLANCE GRID</span>
          </div>

          {currentScope && (
            <button 
              type="button" 
              className="matrix-scope-pill"
              onClick={onOpenScopeSelector}
              title="Click to Switch Active Monitored Sector"
            >
              <MapPin size={12} className="text-emerald" />
              <span>{currentScope.areaName ? `${currentScope.areaName} › ${currentScope.streetName}` : 'All Operational Sectors'}</span>
              <Navigation size={11} className="scope-chevron" />
            </button>
          )}
        </div>

        {/* Right: Layout Switcher & Actions */}
        <div className="matrix-toolbar-actions">
          {defaultCameras.length > 0 && (
            <div className="layout-modes">
              <button 
                type="button"
                className={`layout-btn ${layout === 'solo' ? 'active' : ''}`}
                onClick={() => setLayout('solo')}
                title="Single Focus Camera"
              >
                <Square size={13} />
                <span>SOLO</span>
              </button>
              <button 
                type="button"
                className={`layout-btn ${layout === 'grid4' ? 'active' : ''}`}
                onClick={() => setLayout('grid4')}
                title="4-Camera Quad Grid"
              >
                <Grid2X2 size={13} />
                <span>4-GRID</span>
              </button>
              <button 
                type="button"
                className={`layout-btn ${layout === 'grid8' ? 'active' : ''}`}
                onClick={() => setLayout('grid8')}
                title="8-Camera Tactical Wall"
              >
                <LayoutGrid size={13} />
                <span>8-GRID</span>
              </button>
            </div>
          )}

          {onOpenConfigModal && (
            <button 
              type="button"
              className="connect-camera-btn"
              onClick={onOpenConfigModal}
              title="Register and Connect New CCTV Cameras"
            >
              <Plus size={14} />
              <span>CONNECT CCTV</span>
            </button>
          )}
        </div>
      </div>

      {/* Stream Camera Switcher Pills */}
      {defaultCameras.length > 0 && (
        <div className="matrix-cams-bar">
          <div className="cam-tabs">
            {defaultCameras.map(cam => {
              const isSelected = selectedCamId === cam.id;
              const isAlerting = activeAlertCamId === cam.id;
              return (
                <button
                  key={cam.id}
                  type="button"
                  onClick={() => {
                    onSelectCam(cam.id);
                    if (layout !== 'solo') setLayout('solo');
                  }}
                  className={`cam-tab-btn ${isSelected ? 'active' : ''} ${isAlerting ? 'alerting' : ''}`}
                  title={`${cam.name} (${cam.streetName || ''})`}
                >
                  <span className={`cam-status-indicator ${cam.active ? 'active' : 'inactive'}`} />
                  <span className="cam-tab-name">{cam.name}</span>
                  {cam.streetName && <span className="cam-type-tag">{cam.streetName}</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Zero State */}
      {defaultCameras.length === 0 ? (
        <div className="matrix-empty-state">
          <div className="empty-state-card">
            <div className="empty-icon-pulse">
              <Layers size={40} className="text-indigo" />
            </div>
            <h3>No Surveillance Cameras Configured</h3>
            <p className="empty-state-subtitle">
              Configure your monitored areas, streets, and CCTV cameras to begin AI threat monitoring.
            </p>
            <button 
              type="button" 
              className="exec-submit-btn"
              onClick={onOpenConfigModal}
            >
              <Plus size={16} /> Deploy First Camera Feed
            </button>
          </div>
        </div>
      ) : (
        /* Video Grid Container */
        <div className={`matrix-grid layout-${layout}`}>
          {displayCameras.map(cam => {
            const isErrored = imgErrors[cam.id];
            const isSelected = selectedCamId === cam.id;
            const isAlerting = activeAlertCamId === cam.id;

            return (
              <div 
                key={cam.id} 
                className={`video-card ${isSelected ? 'focused' : ''} ${isAlerting ? 'threat-alert' : ''}`}
                onClick={() => onSelectCam(cam.id)}
              >
                {/* Top Video Header Badge */}
                <div className="video-header-overlay">
                  <div className="cam-ident">
                    <span className="live-dot pulse-green"></span>
                    <span className="cam-label-name">{cam.name}</span>
                    <span className="cam-badge-id font-mono">{cam.id.toUpperCase()}</span>
                  </div>

                  <div className="cam-indicators">
                    {isAlerting && (
                      <span className="threat-pill">
                        <Radio size={12} className="pulse-red" /> THREAT ACTIVE
                      </span>
                    )}
                    <span className="fps-pill font-mono">25.0 FPS</span>
                  </div>
                </div>

                {/* Video Stream / Real Live Camera Feed */}
                <div className="video-feed-viewport">
                  {!isErrored && isBackendOnline ? (
                    <img
                      src={`/video_feed/${cam.id}?t=${isSelected ? 'focus' : 'grid'}`}
                      alt={cam.name}
                      className="video-stream-img"
                      onError={() => handleImgError(cam.id)}
                    />
                  ) : (
                    <div className="camera-reconnecting-box">
                      <Camera size={36} className="text-muted pulse-indicator" />
                      <strong>Camera Standby</strong>
                      <p className="reconnect-hint">Verifying DirectShow / RTSP sensor signal...</p>
                      <button 
                        type="button" 
                        className="retry-stream-btn" 
                        onClick={(e) => { e.stopPropagation(); handleRetry(cam.id); }}
                      >
                        <RefreshCw size={13} /> Reconnect Feed
                      </button>
                    </div>
                  )}

                  {/* Bottom Video HUD Strip */}
                  <div className="video-bottom-hud">
                    <span className="hud-tech-text font-mono">
                      YOLOv8x-SURVEILLANCE • DETECTIONS ACTIVE
                    </span>
                    <button 
                      type="button"
                      className="hud-action-btn"
                      title="Focus Camera"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectCam(cam.id);
                        setLayout('solo');
                      }}
                    >
                      <Maximize2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

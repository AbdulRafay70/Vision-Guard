import React, { useState } from 'react';
import { 
  Camera, 
  Grid2X2, 
  Square, 
  LayoutGrid, 
  RefreshCw, 
  Download, 
  Eye, 
  AlertCircle, 
  Radio, 
  SlidersHorizontal, 
  Plus, 
  MapPin, 
  Navigation, 
  Layers 
} from 'lucide-react';

export default function CameraMatrix({ 
  cameras, 
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

  // If user has defined cameras, use them. If none exist at all, defaultCameras is empty
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
    <div className="camera-matrix-wrapper glass-panel">
      {/* Top Matrix Toolbar */}
      <div className="matrix-toolbar">
        <div className="matrix-title-group">
          <Camera size={18} className="text-accent" />
          <span className="matrix-title">CCTV SURVEILLANCE MATRIX</span>
          {currentScope && (
            <span className="matrix-scope-tag">
              {currentScope.areaName ? `${currentScope.areaName} › ${currentScope.streetName}` : 'ALL SECTORS'}
            </span>
          )}
        </div>

        {/* Right Toolbar Actions */}
        <div className="matrix-toolbar-actions">
          {/* Active Sector Scope Switcher */}
          {currentScope && onOpenScopeSelector && (
            <button 
              type="button"
              className="control-btn btn-sector-switch"
              onClick={onOpenScopeSelector}
              title="Switch Active Area / Street View"
            >
              <Navigation size={13} className="text-accent" />
              <span>SWITCH SECTOR</span>
            </button>
          )}

          {/* Add / Connect CCTV Camera Button */}
          {onOpenConfigModal && (
            <button 
              id="toolbar-infra-btn"
              type="button"
              className="control-btn btn-add-camera"
              style={{ background: 'linear-gradient(135deg, rgba(255, 170, 0, 0.25), rgba(255, 85, 0, 0.25))', borderColor: '#ffaa00', color: '#ffcc00', fontWeight: 'bold' }}
              onClick={() => {
                if (typeof onOpenConfigModal === 'function') {
                  onOpenConfigModal();
                }
              }}
              title="Connect Live CCTV Cameras, RTSP or Webcams"
            >
              <Plus size={15} />
              <span>+ CONNECT CCTV</span>
            </button>
          )}

          {/* Layout Grid Mode Switcher */}
          {defaultCameras.length > 0 && (
            <div className="layout-modes">
              <button 
                className={`layout-btn ${layout === 'solo' ? 'active' : ''}`}
                onClick={() => setLayout('solo')}
                title="Single Focus Camera"
              >
                <Square size={14} />
                <span>SOLO</span>
              </button>
              <button 
                className={`layout-btn ${layout === 'grid4' ? 'active' : ''}`}
                onClick={() => setLayout('grid4')}
                title="4-Camera Quad Grid"
              >
                <Grid2X2 size={14} />
                <span>4-GRID</span>
              </button>
              <button 
                className={`layout-btn ${layout === 'grid8' ? 'active' : ''}`}
                onClick={() => setLayout('grid8')}
                title="8-Camera Tactical Wall"
              >
                <LayoutGrid size={14} />
                <span>8-GRID</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Dedicated Full-Width Camera Selector Bar */}
      {defaultCameras.length > 0 && (
        <div className="matrix-cams-bar">
          <span className="cams-bar-label font-mono">FEEDS ({defaultCameras.length}):</span>
          <div className="cam-tabs">
            {defaultCameras.map(cam => (
              <button
                key={cam.id}
                onClick={() => {
                  onSelectCam(cam.id);
                  if (layout !== 'solo') setLayout('solo');
                }}
                className={`cam-tab-btn ${selectedCamId === cam.id ? 'active' : ''} ${activeAlertCamId === cam.id ? 'alerting' : ''}`}
                title={`${cam.name} (${cam.streetName || ''} - ${cam.areaName || ''})`}
              >
                <div className={`cam-status-indicator ${cam.active ? 'active' : 'inactive'}`} />
                <span className="cam-tab-id font-mono">{cam.id.toUpperCase()}</span>
                <span className="cam-tab-name">{cam.name}</span>
                {cam.streetName && <span className="cam-type-tag">{cam.streetName}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Zero State: When no Areas, Streets, or Cameras are configured */}
      {defaultCameras.length === 0 ? (
        <div className="matrix-empty-state">
          <div className="empty-state-card glass-panel">
            <div className="empty-icon-pulse">
              <Layers size={48} className="text-accent" />
            </div>
            <h3>NO SURVEILLANCE INFRASTRUCTURE CONFIGURED</h3>
            <p className="empty-state-subtitle">
              No Areas, Streets, or CCTV Cameras are currently configured in this command dashboard.
            </p>

            <div className="empty-hierarchy-steps">
              <div className="hierarchy-step">
                <div className="step-badge">1</div>
                <div className="step-info">
                  <strong>Define Area</strong>
                  <span>Downtown, Sector A, Industrial Hub</span>
                </div>
              </div>
              <div className="step-divider">&rarr;</div>
              <div className="hierarchy-step">
                <div className="step-badge">2</div>
                <div className="step-info">
                  <strong>Add Street</strong>
                  <span>Main Avenue, 5th Boulevard</span>
                </div>
              </div>
              <div className="step-divider">&rarr;</div>
              <div className="hierarchy-step">
                <div className="step-badge">3</div>
                <div className="step-info">
                  <strong>Deploy Camera</strong>
                  <span>RTSP IP Cam, USB Web, Video Stream</span>
                </div>
              </div>
            </div>

            <button 
              id="add-infrastructure-btn"
              type="button"
              className="empty-cta-btn"
              onClick={() => {
                if (typeof onOpenConfigModal === 'function') {
                  onOpenConfigModal();
                }
              }}
            >
              <Plus size={16} />
              <span>Add Areas, Streets & Cameras Now</span>
            </button>
          </div>
        </div>
      ) : (
        /* Video Streams Container */
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
              {/* Camera Header Overlay */}
              <div className="video-header-overlay">
                <div className="cam-ident">
                  <span className="cam-badge-id font-mono">{cam.id.toUpperCase()}</span>
                  <span className="cam-label-name">{cam.name}</span>
                </div>
                <div className="cam-indicators">
                  {isAlerting && (
                    <span className="threat-pill">
                      <Radio size={12} className="pulse-red" /> THREAT ACTIVE
                    </span>
                  )}
                  <span className="live-pill">
                    <span className="live-dot pulse-green"></span> LIVE
                  </span>
                </div>
              </div>

              {/* Video Stream / MP4 Video Player or Error State */}
              <div className="video-feed-viewport">
                {!isErrored && isBackendOnline ? (
                  <img
                    src={`/video_feed/${cam.id}?t=${isSelected ? 'focus' : 'grid'}`}
                    alt={cam.name}
                    className="video-stream-img"
                    onError={() => handleImgError(cam.id)}
                  />
                ) : (
                  <video
                    src="/4116863-hd_1920_1080_30fps.mp4"
                    className="video-stream-img"
                    autoPlay
                    loop
                    muted
                    playsInline
                  />
                )}

                {/* Tactical HUD Corner Crosshairs */}
                <div className="hud-corner top-left"></div>
                <div className="hud-corner top-right"></div>
                <div className="hud-corner bottom-left"></div>
                <div className="hud-corner bottom-right"></div>

                {/* Subtitle / Timestamp bar */}
                <div className="video-bottom-hud">
                  <span className="hud-tech-text font-mono">
                    {cam.stats?.display_fps ? `${cam.stats.display_fps} FPS • ${cam.stats.avg_frame_age_ms || 20}ms` : 'REC [AI-PASS ACTIVE] • DECOUPLED'}
                  </span>
                  <div className="hud-action-icons">
                    <button 
                      className="hud-action-btn"
                      title="Download Frame"
                      onClick={(e) => {
                        e.stopPropagation();
                        window.open(`/video_feed/${cam.id}`, '_blank');
                      }}
                    >
                      <Download size={14} />
                    </button>
                  </div>
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

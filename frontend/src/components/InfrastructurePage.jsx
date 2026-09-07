import React, { useState, useRef, useEffect } from 'react';
import { 
  Plus, 
  Camera, 
  Video, 
  Upload, 
  Play, 
  CheckCircle2, 
  AlertCircle, 
  Trash2, 
  RefreshCw, 
  Layers, 
  MapPin, 
  Navigation,
  Eye,
  Radio,
  FileVideo,
  Square,
  VideoOff
} from 'lucide-react';

export default function InfrastructurePage({ 
  areas = [], 
  onSaveAreas, 
  onRefreshCameras,
  onNavigateToDashboard
}) {
  const [activeSubTab, setActiveSubTab] = useState('deploy'); // 'deploy' | 'areas' | 'grid'

  // Flatten all deployed cameras for easy overview & instant deletion
  const allDeployedCameras = areas.flatMap(area => 
    (area.streets || []).flatMap(street => 
      (street.cameras || []).map(cam => ({
        ...cam,
        areaId: area.id,
        areaName: area.name,
        streetId: street.id,
        streetName: street.name,
        sector: street.sector
      }))
    )
  );
  
  // Registration Form State
  const [selectedAreaId, setSelectedAreaId] = useState(areas[0]?.id || '');
  const [selectedStreetId, setSelectedStreetId] = useState(areas[0]?.streets?.[0]?.id || '');
  const [camId, setCamId] = useState('');
  const [camName, setCamName] = useState('');
  const [camType, setCamType] = useState('webcam'); // 'webcam' | 'rtsp' | 'video'
  const [camSource, setCamSource] = useState('1');

  // Video Upload State
  const [uploading, setUploading] = useState(false);
  const [uploadedVideoUrl, setUploadedVideoUrl] = useState('');
  const [uploadError, setUploadError] = useState('');

  // Live Webcam Browser Test State
  const [webcamTesting, setWebcamTesting] = useState(false);
  const [webcamError, setWebcamError] = useState('');
  const videoTestRef = useRef(null);

  // Status notifications
  const [notification, setNotification] = useState({ text: '', type: '' });

  // Camera Ping / Test Connection State
  const [testingConn, setTestingConn] = useState(false);
  const [testConnResult, setTestConnResult] = useState(null);

  const handleTestConnection = async () => {
    if (!camSource) {
      showNotify("Please enter a stream URL, device index, or file source first.", "error");
      return;
    }
    setTestingConn(true);
    setTestConnResult(null);
    try {
      const res = await fetch('/api/cameras/test-connection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: camType,
          source: camSource
        })
      });
      const data = await res.json();
      setTestConnResult(data);
      if (res.ok && data.status === 'online') {
        showNotify("Camera stream connection verified successfully!");
      } else {
        showNotify(data.message || "Camera stream test failed", "error");
      }
    } catch (err) {
      setTestConnResult({ status: 'offline', message: 'Connection test error: ' + err.message });
      showNotify("Connection ping failed: " + err.message, "error");
    } finally {
      setTestingConn(false);
    }
  };

  // Area & Street Creator Form State
  const [newAreaName, setNewAreaName] = useState('');
  const [newStreetName, setNewStreetName] = useState('');
  const [newStreetSector, setNewStreetSector] = useState('');
  const [targetAreaForStreet, setTargetAreaForStreet] = useState(areas[0]?.id || '');

  // Keep street selection in sync when area changes
  useEffect(() => {
    const currentArea = areas.find(a => a.id === selectedAreaId) || areas[0];
    if (currentArea && currentArea.streets?.length > 0) {
      if (!currentArea.streets.some(s => s.id === selectedStreetId)) {
        setSelectedStreetId(currentArea.streets[0].id);
      }
    }
  }, [selectedAreaId, areas]);

  const showNotify = (text, type = 'success') => {
    setNotification({ text, type });
    setTimeout(() => setNotification({ text: '', type: '' }), 4000);
  };

  // Start live browser webcam preview
  const startWebcamPreview = async () => {
    setWebcamError('');
    try {
      setWebcamTesting(true);
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 1280, height: 720 } 
      });
      if (videoTestRef.current) {
        videoTestRef.current.srcObject = stream;
        videoTestRef.current.play();
      }
    } catch (err) {
      console.warn("Webcam access error:", err);
      setWebcamError("Could not access browser camera: " + (err.message || 'Permission denied'));
      setWebcamTesting(false);
    }
  };

  const stopWebcamPreview = () => {
    if (videoTestRef.current && videoTestRef.current.srcObject) {
      const tracks = videoTestRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
      videoTestRef.current.srcObject = null;
    }
    setWebcamTesting(false);
  };

  // Handle 5-10s video clip upload
  const handleVideoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/cameras/upload-test-video', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setUploadedVideoUrl(data.preview_url);
        setCamSource(data.path);
        setCamType('video');
        if (!camName) {
          setCamName(`Test Clip: ${file.name.replace(/\.[^/.]+$/, "")}`);
        }
        showNotify(`Uploaded "${file.name}" successfully! Preview loaded.`);
      } else {
        setUploadError(data.detail || 'Upload failed');
      }
    } catch (err) {
      setUploadError("Network error uploading video: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  // Submit and deploy camera to grid
  const handleDeployCamera = async (e) => {
    e.preventDefault();
    if (!camName.trim()) {
      showNotify("Please enter a Camera Label / Name.", "error");
      return;
    }

    const currentArea = areas.find(a => a.id === selectedAreaId);
    if (!currentArea) {
      showNotify("Please select or create an Area first.", "error");
      return;
    }

    const currentStreet = (currentArea.streets || []).find(s => s.id === selectedStreetId);
    if (!currentStreet) {
      showNotify("Please select or create a Street/Sector first.", "error");
      return;
    }

    const newId = camId.trim() 
      ? camId.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_')
      : `cam_${Date.now().toString().slice(-4)}`;

    let backendSource = camSource.trim();
    if (camType === 'webcam') {
      backendSource = parseInt(camSource, 10) || 0;
    }

    // Connect dynamically to backend AI stream
    try {
      const res = await fetch('/api/cameras/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: newId,
          name: camName.trim(),
          type: camType,
          source: backendSource
        })
      });
      const data = await res.json();
      console.log("Connect response:", data);
    } catch (err) {
      console.warn("Backend dynamic connect error:", err);
    }

    // Add to hierarchy state
    const newCameraObj = {
      id: newId,
      name: camName.trim(),
      type: camType,
      source: camSource,
      active: true,
      enabled: true,
      areaId: currentArea.id,
      areaName: currentArea.name,
      streetId: currentStreet.id,
      streetName: currentStreet.name
    };

    const updated = areas.map(a => {
      if (a.id === currentArea.id) {
        return {
          ...a,
          streets: a.streets.map(s => {
            if (s.id === currentStreet.id) {
              return {
                ...s,
                cameras: [...(s.cameras || []).filter(c => c.id !== newId), newCameraObj]
              };
            }
            return s;
          })
        };
      }
      return a;
    });

    onSaveAreas(updated);
    stopWebcamPreview();
    showNotify(`Camera "${camName}" deployed to ${currentArea.name} › ${currentStreet.name}!`);
    setCamName('');
    setCamId('');
  };

  // Add Area
  const handleAddArea = (e) => {
    e.preventDefault();
    if (!newAreaName.trim()) return;
    const newId = `area_${Date.now().toString().slice(-4)}`;
    const updated = [
      ...areas,
      {
        id: newId,
        name: newAreaName.trim(),
        streets: []
      }
    ];
    onSaveAreas(updated);
    setNewAreaName('');
    setSelectedAreaId(newId);
    showNotify(`Area "${newAreaName}" added!`);
  };

  // Add Street
  const handleAddStreet = (e) => {
    e.preventDefault();
    if (!newStreetName.trim() || !targetAreaForStreet) return;
    const streetId = `street_${Date.now().toString().slice(-4)}`;
    const updated = areas.map(a => {
      if (a.id === targetAreaForStreet) {
        return {
          ...a,
          streets: [
            ...(a.streets || []),
            {
              id: streetId,
              name: newStreetName.trim(),
              sector: newStreetSector.trim() || 'Sector 1',
              cameras: []
            }
          ]
        };
      }
      return a;
    });
    onSaveAreas(updated);
    setNewStreetName('');
    setNewStreetSector('');
    setSelectedStreetId(streetId);
    showNotify(`Street "${newStreetName}" added to area!`);
  };

  // Delete camera
  const handleDeleteCamera = async (areaId, streetId, cameraDelId) => {
    try {
      await fetch(`/api/cameras/disconnect/${cameraDelId}`, { method: 'POST' });
    } catch (e) {}

    const updated = areas.map(a => {
      if (a.id === areaId) {
        return {
          ...a,
          streets: a.streets.map(s => {
            if (s.id === streetId) {
              return {
                ...s,
                cameras: (s.cameras || []).filter(c => c.id !== cameraDelId)
              };
            }
            return s;
          })
        };
      }
      return a;
    });
    onSaveAreas(updated);
    showNotify(`Camera removed.`);
  };

  return (
    <div className="infra-page-container">
      {/* Page Header */}
      <div className="infra-page-header">
        <div>
          <div className="infra-badge-tag">CCTV INFRASTRUCTURE & TESTING</div>
          <h2 className="infra-main-title">Surveillance Hardware & Test Registration</h2>
          <p className="infra-subtitle">
            Register real CCTV cameras (Webcam/OBS, RTSP IP stream) or upload 5–10s video clips with live browser preview before deploying to city sectors.
          </p>
        </div>

        {/* Sub-tabs switch */}
        <div className="infra-subtab-bar">
          <button 
            type="button" 
            className={`subtab-btn ${activeSubTab === 'deploy' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('deploy')}
          >
            <Camera size={16} /> Deploy & Test Camera
          </button>
          <button 
            type="button" 
            className={`subtab-btn ${activeSubTab === 'areas' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('areas')}
          >
            <MapPin size={16} /> Manage Areas & Streets
          </button>
          <button 
            type="button" 
            className={`subtab-btn ${activeSubTab === 'grid' ? 'active' : ''}`}
            onClick={() => setActiveSubTab('grid')}
          >
            <Layers size={16} /> Infrastructure Tree ({areas.reduce((acc, a) => acc + (a.streets || []).reduce((sc, s) => sc + (s.cameras || []).length, 0), 0)} Cams)
          </button>
        </div>
      </div>

      {notification.text && (
        <div className={`infra-alert-banner ${notification.type === 'error' ? 'banner-error' : 'banner-success'}`}>
          {notification.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />}
          <span>{notification.text}</span>
        </div>
      )}

      {/* SUB-TAB 1: DEPLOY & TEST CAMERA */}
      {activeSubTab === 'deploy' && (
        <>
          <div className="infra-grid-layout">
          {/* Left Column: Camera Configuration Form */}
          <div className="exec-card form-card">
            <h3 className="section-title">
              <Plus size={20} className="text-indigo" /> Register New Camera Feed
            </h3>
            
            <form onSubmit={handleDeployCamera} className="exec-form">
              {/* 1. Area & Street Selection */}
              <div className="form-row-2">
                <div className="input-group">
                  <label>1. Target City Area</label>
                  <select 
                    value={selectedAreaId} 
                    onChange={e => setSelectedAreaId(e.target.value)}
                    className="exec-select"
                  >
                    {areas.map(a => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                </div>

                <div className="input-group">
                  <label>2. Street / Sector</label>
                  <select 
                    value={selectedStreetId} 
                    onChange={e => setSelectedStreetId(e.target.value)}
                    className="exec-select"
                  >
                    {(areas.find(a => a.id === selectedAreaId)?.streets || []).map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.sector})</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* 2. Camera Name & Identifier */}
              <div className="form-row-2">
                <div className="input-group">
                  <label>Camera Label / Location *</label>
                  <input 
                    type="text" 
                    placeholder="e.g. V380 Street Cam, North Gate"
                    value={camName}
                    onChange={e => setCamName(e.target.value)}
                    className="exec-input"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>Identifier (Optional ID)</label>
                  <input 
                    type="text" 
                    placeholder="e.g. cam_v380_street"
                    value={camId}
                    onChange={e => setCamId(e.target.value)}
                    className="exec-input font-mono"
                  />
                </div>
              </div>

              {/* 3. Stream Feed Type */}
              <div className="input-group">
                <label>Stream Feed Source Protocol</label>
                <div className="protocol-selector-row">
                  <button 
                    type="button" 
                    className={`protocol-btn ${camType === 'webcam' ? 'active' : ''}`}
                    onClick={() => { setCamType('webcam'); setCamSource('1'); }}
                  >
                    <Camera size={18} />
                    <span>USB / OBS Virtual Cam</span>
                  </button>

                  <button 
                    type="button" 
                    className={`protocol-btn ${camType === 'rtsp' ? 'active' : ''}`}
                    onClick={() => { setCamType('rtsp'); setCamSource('rtsp://192.168.1.64:554/stream'); }}
                  >
                    <Radio size={18} />
                    <span>RTSP IP Camera (PoE)</span>
                  </button>

                  <button 
                    type="button" 
                    className={`protocol-btn ${camType === 'video' ? 'active' : ''}`}
                    onClick={() => { setCamType('video'); }}
                  >
                    <FileVideo size={18} />
                    <span>5–10s Video Clip File</span>
                  </button>
                </div>
              </div>

              {/* 4. Stream Source Value Input */}
              {camType === 'webcam' && (
                <div className="input-group">
                  <label>Camera Device Index</label>
                  <div className="source-input-row">
                    <input 
                      type="number" 
                      min="0" 
                      max="10" 
                      value={camSource}
                      onChange={e => setCamSource(e.target.value)}
                      className="exec-input font-mono"
                    />
                    <span className="helper-text">
                      Index <strong>0</strong> = Integrated Laptop Webcam. Index <strong>1</strong> = OBS Virtual Camera (V380).
                    </span>
                  </div>
                </div>
              )}

              {camType === 'rtsp' && (
                <div className="space-y-3">
                  <div className="input-group">
                    <label>RTSP / IP Stream URL *</label>
                    <input 
                      type="text" 
                      placeholder="rtsp://admin:password@192.168.1.100:554/h264"
                      value={camSource}
                      onChange={e => setCamSource(e.target.value)}
                      className="exec-input font-mono"
                      required
                    />
                    <span className="helper-text">Supports H.264 / H.265 streams from Hikvision, Dahua, Uniview, V380, and ONVIF NVRs.</span>
                  </div>

                  {/* Preset RTSP Helper Links */}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => setCamSource('rtsp://admin:admin123@192.168.1.108:554/cam/realmonitor?channel=1&subtype=0')}
                      className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 rounded text-slate-700 dark:text-slate-300 font-mono"
                    >
                      Dahua Preset
                    </button>
                    <button
                      type="button"
                      onClick={() => setCamSource('rtsp://admin:admin123@192.168.1.64:554/Streaming/Channels/101')}
                      className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 rounded text-slate-700 dark:text-slate-300 font-mono"
                    >
                      Hikvision Preset
                    </button>
                    <button
                      type="button"
                      onClick={() => setCamSource('http://192.168.1.50:8080/video')}
                      className="px-2.5 py-1 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 rounded text-slate-700 dark:text-slate-300 font-mono"
                    >
                      MJPEG IP Stream
                    </button>
                  </div>
                </div>
              )}

              {camType === 'video' && (
                <div className="input-group">
                  <label>Video File Path or Preset</label>
                  <input 
                    type="text" 
                    value={camSource}
                    onChange={e => setCamSource(e.target.value)}
                    className="exec-input font-mono"
                  />
                  <div className="preset-chips">
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Enter webcam device index (e.g. 0), RTSP stream URL (rtsp://...), or upload video file.
                    </span>
                  </div>
                </div>
              )}

              {/* Ping / Test Stream Connection Bar */}
              <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <button
                  type="button"
                  onClick={handleTestConnection}
                  disabled={testingConn}
                  className="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-800 hover:bg-slate-900 text-white font-medium rounded-xl transition text-sm disabled:opacity-50"
                >
                  {testingConn ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-emerald-400" />
                      <span>Testing Stream Ping...</span>
                    </>
                  ) : (
                    <>
                      <Radio className="w-4 h-4 text-emerald-400" />
                      <span>Test Stream Connection</span>
                    </>
                  )}
                </button>

                {testConnResult && (
                  <div className={`p-2.5 rounded-xl border text-xs flex items-center gap-2 font-mono flex-1 ${
                    testConnResult.status === 'online'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                      : 'bg-red-500/10 border-red-500/30 text-red-600 dark:text-red-400'
                  }`}>
                    {testConnResult.status === 'online' ? <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-500" /> : <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />}
                    <span>{testConnResult.message} {testConnResult.latency_ms ? `(${testConnResult.latency_ms}ms)` : ''}</span>
                  </div>
                )}
              </div>

              <button type="submit" className="exec-submit-btn">
                <Plus size={18} /> Deploy Camera to Surveillance Grid
              </button>
            </form>
          </div>

          {/* Right Column: Live Testing Sandbox & Video Uploader */}
          <div className="exec-card sandbox-card">
            <h3 className="section-title">
              <Eye size={20} className="text-indigo" /> Live Hardware Testing Sandbox
            </h3>
            <p className="sandbox-desc">
              Test your camera feed or upload a 5–10s video clip right here to verify visual quality and alignment before deploying.
            </p>

            {/* Upload Video Clip Box */}
            <div className="upload-box">
              <div className="upload-box-content">
                <Upload size={28} className="upload-icon text-indigo" />
                <div className="upload-text">
                  <strong>Upload 5–10s Test Video Clip</strong>
                  <span>Supports MP4, AVI, MOV clips</span>
                </div>
              </div>
              <input 
                type="file" 
                accept="video/*" 
                onChange={handleVideoUpload}
                disabled={uploading}
                className="file-input-hidden"
                id="test-video-file-input"
              />
              <label htmlFor="test-video-file-input" className="upload-action-btn">
                {uploading ? <RefreshCw size={16} className="spin" /> : <Upload size={16} />}
                <span>{uploading ? 'Uploading...' : 'Choose Video File'}</span>
              </label>
            </div>

            {uploadError && <div className="sandbox-error">{uploadError}</div>}

            {/* Video Clip Player Preview */}
            {uploadedVideoUrl && (
              <div className="preview-container">
                <div className="preview-header">
                  <span className="preview-tag">Uploaded Video Preview</span>
                  <span className="preview-status">Ready for Deployment</span>
                </div>
                <video 
                  src={uploadedVideoUrl} 
                  controls 
                  autoPlay 
                  loop 
                  className="sandbox-video"
                />
              </div>
            )}

            {/* Webcam Live Test Section */}
            <div className="webcam-test-box">
              <div className="webcam-controls-row">
                <div className="webcam-info">
                  <strong>Browser Webcam / OBS Test</strong>
                  <span>Verify your camera sensor or OBS virtual camera in real time.</span>
                </div>
                <div className="webcam-btn-group">
                  {!webcamTesting ? (
                    <button type="button" onClick={startWebcamPreview} className="test-stream-btn start">
                      <Camera size={16} /> Start Webcam Preview
                    </button>
                  ) : (
                    <button type="button" onClick={stopWebcamPreview} className="test-stream-btn stop">
                      <Square size={16} fill="currentColor" /> Stop Webcam
                    </button>
                  )}
                </div>
              </div>

              {webcamError && <div className="sandbox-error">{webcamError}</div>}

              {webcamTesting && (
                <div className="preview-container">
                  <video 
                    ref={videoTestRef} 
                    autoPlay 
                    playsInline 
                    muted 
                    className="sandbox-video live-preview"
                  />
                  <div className="live-indicator-chip">
                    <span className="live-dot pulse-red"></span> LIVE PREVIEW
                  </div>
                  <button 
                    type="button" 
                    onClick={stopWebcamPreview} 
                    className="preview-floating-stop-btn"
                    title="Stop Webcam Preview"
                  >
                    <VideoOff size={14} />
                    <span>Stop Camera</span>
                  </button>
                </div>
              )}
            </div>

            {/* Quick Navigation to Dashboard */}
            <div className="sandbox-footer">
              <button 
                type="button" 
                className="dashboard-link-btn"
                onClick={onNavigateToDashboard}
              >
                <span>View Live Grid in Dashboard &rarr;</span>
              </button>
            </div>
          </div>
        </div>

        {/* Full-Width Manage & Delete Active CCTV Feeds Card */}
        <div className="exec-card deployed-cams-card">
          <div className="card-header-between">
            <div className="title-with-badge">
              <Camera size={20} className="text-indigo" />
              <h3 className="section-title">Active Deployed CCTV Feeds ({allDeployedCameras.length})</h3>
            </div>
            <span className="badge-pill badge-dark font-mono">1-CLICK DISCONNECT / REMOVE</span>
          </div>

          {allDeployedCameras.length === 0 ? (
            <div className="empty-cams-box">
              <p>No CCTV cameras registered yet. Use the form above to register your first camera feed.</p>
            </div>
          ) : (
            <div className="deployed-cams-grid">
              {allDeployedCameras.map(cam => (
                <div key={cam.id} className="deployed-cam-card">
                  <div className="deployed-cam-header">
                    <div className="cam-title-box">
                      <span className="live-dot pulse-green"></span>
                      <strong>{cam.name}</strong>
                    </div>
                    <span className="cam-type-pill">{cam.type.toUpperCase()}</span>
                  </div>

                  <div className="deployed-cam-body">
                    <div className="cam-detail-item">
                      <MapPin size={14} className="text-muted" />
                      <span>{cam.areaName} › {cam.streetName}</span>
                    </div>
                    <div className="cam-detail-item">
                      <Radio size={14} className="text-muted" />
                      <span className="font-mono text-truncate">Source: {String(cam.source)}</span>
                    </div>
                  </div>

                  <div className="deployed-cam-footer">
                    <button
                      type="button"
                      className="delete-cctv-btn"
                      onClick={() => handleDeleteCamera(cam.areaId, cam.streetId, cam.id)}
                      title={`Remove ${cam.name} from CCTV Surveillance Grid`}
                    >
                      <Trash2 size={15} />
                      <span>Delete Camera</span>
                    </button>
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </>
  )}

      {/* SUB-TAB 2: MANAGE AREAS & STREETS */}
      {activeSubTab === 'areas' && (
        <div className="infra-grid-layout">
          {/* Add Area */}
          <div className="exec-card">
            <h3 className="section-title"><MapPin size={20} className="text-indigo" /> Create Urban City Area</h3>
            <form onSubmit={handleAddArea} className="exec-form">
              <div className="input-group">
                <label>Area Name (e.g. Saddar Commercial, Clifton Block 5, Gulshan)</label>
                <input 
                  type="text" 
                  placeholder="e.g. Saddar Central Grid"
                  value={newAreaName}
                  onChange={e => setNewAreaName(e.target.value)}
                  className="exec-input"
                  required
                />
              </div>
              <button type="submit" className="exec-submit-btn">
                <Plus size={16} /> Create Area
              </button>
            </form>
          </div>

          {/* Add Street */}
          <div className="exec-card">
            <h3 className="section-title"><Navigation size={20} className="text-indigo" /> Add Street / Sector</h3>
            <form onSubmit={handleAddStreet} className="exec-form">
              <div className="input-group">
                <label>Parent Area</label>
                <select 
                  value={targetAreaForStreet} 
                  onChange={e => setTargetAreaForStreet(e.target.value)}
                  className="exec-select"
                >
                  {areas.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-row-2">
                <div className="input-group">
                  <label>Street / Road Name</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Empress Market Boulevard"
                    value={newStreetName}
                    onChange={e => setNewStreetName(e.target.value)}
                    className="exec-input"
                    required
                  />
                </div>

                <div className="input-group">
                  <label>Sector / Zone Code</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Sector 1A"
                    value={newStreetSector}
                    onChange={e => setNewStreetSector(e.target.value)}
                    className="exec-input font-mono"
                  />
                </div>
              </div>

              <button type="submit" className="exec-submit-btn">
                <Plus size={16} /> Add Street
              </button>
            </form>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: INFRASTRUCTURE HIERARCHY TREE */}
      {activeSubTab === 'grid' && (
        <div className="infra-tree-container">
          {areas.map(area => (
            <div key={area.id} className="exec-card tree-area-card">
              <div className="tree-area-header">
                <div className="tree-area-title">
                  <MapPin size={22} className="text-indigo" />
                  <h4>{area.name}</h4>
                  <span className="badge-pill badge-dark">{(area.streets || []).length} Streets</span>
                </div>
              </div>

              <div className="tree-streets-grid">
                {(area.streets || []).map(street => (
                  <div key={street.id} className="tree-street-box">
                    <div className="street-header-row">
                      <div className="street-title">
                        <Navigation size={16} className="text-muted" />
                        <strong>{street.name}</strong>
                        <span className="sector-tag">{street.sector}</span>
                      </div>
                      <span className="cams-count-badge">{(street.cameras || []).length} Cameras</span>
                    </div>

                    <div className="street-cams-list">
                      {(street.cameras || []).length === 0 ? (
                        <div className="no-cams-hint">No cameras deployed on this street yet.</div>
                      ) : (
                        (street.cameras || []).map(cam => (
                          <div key={cam.id} className="tree-cam-row">
                            <div className="cam-meta">
                              <span className="live-dot pulse-green"></span>
                              <strong>{cam.name}</strong>
                              <span className="cam-type-pill">{cam.type.toUpperCase()}</span>
                              <span className="cam-source-pill font-mono">{String(cam.source)}</span>
                            </div>
                            <button 
                              type="button" 
                              className="delete-cam-btn"
                              onClick={() => handleDeleteCamera(area.id, street.id, cam.id)}
                              title="Disconnect and remove camera"
                            >
                              <Trash2 size={16} />
                            </button>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

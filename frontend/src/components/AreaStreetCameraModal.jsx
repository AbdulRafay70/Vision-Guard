import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  MapPin, 
  Navigation, 
  Camera, 
  Trash2, 
  X, 
  Layers, 
  CheckCircle2, 
  AlertCircle,
  Video
} from 'lucide-react';

export default function AreaStreetCameraModal({ 
  isOpen, 
  onClose, 
  areas, 
  onSaveAreas 
}) {
  // If no areas exist yet, start on Area tab; otherwise default to Camera deployment
  const [activeTab, setActiveTab] = useState('area');
  
  useEffect(() => {
    if (isOpen) {
      if (!areas || areas.length === 0) {
        setActiveTab('area');
      } else {
        const hasStreets = areas.some(a => a.streets && a.streets.length > 0);
        if (!hasStreets) {
          setActiveTab('street');
        } else {
          setActiveTab('camera');
        }
      }
    }
  }, [isOpen, areas]);
  
  // Forms state
  const [newAreaName, setNewAreaName] = useState('');
  const [newAreaCode, setNewAreaCode] = useState('');

  const [selectedAreaIdForStreet, setSelectedAreaIdForStreet] = useState('');
  const [newStreetName, setNewStreetName] = useState('');
  const [newStreetSector, setNewStreetSector] = useState('');

  const [selectedAreaIdForCam, setSelectedAreaIdForCam] = useState('');
  const [selectedStreetIdForCam, setSelectedStreetIdForCam] = useState('');
  const [newCamId, setNewCamId] = useState('');
  const [newCamName, setNewCamName] = useState('');
  const [newCamType, setNewCamType] = useState('rtsp');
  const [newCamSource, setNewCamSource] = useState('');

  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  if (!isOpen) return null;

  const showNotification = (success, error = '') => {
    setSuccessMsg(success);
    setErrorMsg(error);
    if (success) {
      setTimeout(() => setSuccessMsg(''), 3500);
    }
  };

  // 1. Add Area
  const handleAddArea = (e) => {
    e.preventDefault();
    if (!newAreaName.trim()) {
      showNotification('', 'Please specify an Area Name.');
      return;
    }

    const areaId = newAreaCode.trim() 
      ? newAreaCode.trim().toLowerCase().replace(/\s+/g, '_') 
      : `area_${Date.now()}`;

    // Check duplicate
    if (areas.some(a => a.id === areaId)) {
      showNotification('', `Area ID/Code "${areaId}" already exists.`);
      return;
    }

    const updated = [
      ...areas,
      {
        id: areaId,
        name: newAreaName.trim(),
        streets: []
      }
    ];

    onSaveAreas(updated);
    setNewAreaName('');
    setNewAreaCode('');
    setSelectedAreaIdForStreet(areaId);
    setSelectedAreaIdForCam(areaId);
    showNotification(`Area "${newAreaName.trim()}" added! Now add a Street.`);
    // Automatically transition user to next step
    setTimeout(() => setActiveTab('street'), 600);
  };

  // 2. Add Street to Area
  const handleAddStreet = (e) => {
    e.preventDefault();
    const targetAreaId = selectedAreaIdForStreet || (areas[0]?.id);
    if (!targetAreaId) {
      showNotification('', 'No Area selected. Please add an Area first.');
      return;
    }
    if (!newStreetName.trim()) {
      showNotification('', 'Please provide a Street Name.');
      return;
    }

    const streetId = `street_${Date.now()}`;
    const updated = areas.map(a => {
      if (a.id === targetAreaId) {
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
    setSelectedAreaIdForCam(targetAreaId);
    setSelectedStreetIdForCam(streetId);
    showNotification(`Street "${newStreetName.trim()}" added! Now deploy a Camera.`);
    // Automatically transition user to camera deployment step
    setTimeout(() => setActiveTab('camera'), 600);
  };

  // 3. Add Camera to Street
  const handleAddCamera = async (e) => {
    e.preventDefault();
    const targetAreaId = selectedAreaIdForCam || (areas[0]?.id);
    const targetArea = areas.find(a => a.id === targetAreaId);
    
    if (!targetArea) {
      showNotification('', 'Please select a valid Area.');
      return;
    }

    const targetStreetId = selectedStreetIdForCam || (targetArea.streets?.[0]?.id);
    const targetStreet = targetArea.streets?.find(s => s.id === targetStreetId);

    if (!targetStreet) {
      showNotification('', 'No Street selected. Please create or choose a Street first.');
      return;
    }

    if (!newCamName.trim()) {
      showNotification('', 'Please enter a Camera Name or Label.');
      return;
    }

    const camId = newCamId.trim() 
      ? newCamId.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_')
      : `cam_${Date.now().toString().slice(-4)}`;

    // Check if camera ID already exists anywhere
    const allCams = areas.flatMap(a => (a.streets || []).flatMap(s => s.cameras || []));
    if (allCams.some(c => c.id === camId)) {
      showNotification('', `Camera ID "${camId}" is already registered.`);
      return;
    }

    let sourceVal = newCamSource.trim() || 'prototype/test_videos/4116863-hd_1920_1080_30fps.mp4';
    let backendSource = sourceVal;
    if (newCamType === 'webcam') {
      backendSource = sourceVal ? parseInt(sourceVal, 10) : 0;
    } else if (newCamType === 'video' && backendSource.startsWith('/')) {
      backendSource = `prototype/test_videos${backendSource}`;
    }

    // Call backend API /api/cameras/connect
    try {
      await fetch('/api/cameras/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: camId,
          name: newCamName.trim(),
          type: newCamType,
          source: backendSource
        })
      });
    } catch (err) {
      console.warn("Backend camera connect error:", err);
    }

    const newCamera = {
      id: camId,
      name: newCamName.trim(),
      type: newCamType,
      source: sourceVal,
      videoUrl: null,
      enabled: true,
      active: true,
      areaId: targetArea.id,
      areaName: targetArea.name,
      streetId: targetStreet.id,
      streetName: targetStreet.name
    };

    const updated = areas.map(a => {
      if (a.id === targetArea.id) {
        return {
          ...a,
          streets: a.streets.map(s => {
            if (s.id === targetStreet.id) {
              return {
                ...s,
                cameras: [...(s.cameras || []), newCamera]
              };
            }
            return s;
          })
        };
      }
      return a;
    });

    onSaveAreas(updated);
    setNewCamId('');
    setNewCamName('');
    setNewCamSource('');
    showNotification(`Camera "${newCamName.trim()}" (${camId}) deployed successfully!`);
  };

  // Delete camera
  const handleDeleteCamera = async (camId) => {
    try {
      await fetch(`/api/cameras/disconnect/${camId}`, { method: 'POST' });
    } catch (err) {
      console.warn("Backend camera disconnect error:", err);
    }
    const updated = areas.map(a => ({
      ...a,
      streets: (a.streets || []).map(s => ({
        ...s,
        cameras: (s.cameras || []).filter(c => c.id !== camId)
      }))
    }));
    onSaveAreas(updated);
    showNotification(`Camera ${camId} removed.`);
  };

  // Delete street
  const handleDeleteStreet = (areaId, streetId) => {
    const updated = areas.map(a => {
      if (a.id === areaId) {
        return {
          ...a,
          streets: (a.streets || []).filter(s => s.id !== streetId)
        };
      }
      return a;
    });
    onSaveAreas(updated);
    showNotification('Street and attached cameras deleted.');
  };

  // Delete area
  const handleDeleteArea = (areaId) => {
    const updated = areas.filter(a => a.id !== areaId);
    onSaveAreas(updated);
    showNotification('Area deleted.');
  };

  const selectedAreaForCamObj = areas.find(a => a.id === (selectedAreaIdForCam || areas[0]?.id));
  const streetsForSelectedArea = selectedAreaForCamObj?.streets || [];

  return (
    <div className="infrastructure-modal-backdrop" onClick={onClose}>
      <div className="infrastructure-modal-card glass-panel" onClick={e => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="infrastructure-modal-header">
          <div className="infrastructure-modal-title">
            <Layers className="text-accent" size={20} />
            <div>
              <h3>Surveillance Infrastructure Configuration</h3>
              <p>Register Areas &rarr; Streets &rarr; CCTV Cameras</p>
            </div>
          </div>
          <button className="infra-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="infra-tabs-bar">
          <button 
            className={`infra-tab-btn ${activeTab === 'camera' ? 'active' : ''}`}
            onClick={() => setActiveTab('camera')}
          >
            <Camera size={14} />
            <span>Deploy Camera</span>
          </button>
          <button 
            className={`infra-tab-btn ${activeTab === 'street' ? 'active' : ''}`}
            onClick={() => setActiveTab('street')}
          >
            <Navigation size={14} />
            <span>Add Street</span>
          </button>
          <button 
            className={`infra-tab-btn ${activeTab === 'area' ? 'active' : ''}`}
            onClick={() => setActiveTab('area')}
          >
            <MapPin size={14} />
            <span>Add Area</span>
          </button>
          <button 
            className={`infra-tab-btn ${activeTab === 'manage' ? 'active' : ''}`}
            onClick={() => setActiveTab('manage')}
          >
            <Layers size={14} />
            <span>Hierarchy Tree ({areas.length} Areas)</span>
          </button>
        </div>

        {/* Feedback Messages */}
        {successMsg && (
          <div className="infra-alert-banner success">
            <CheckCircle2 size={16} />
            <span>{successMsg}</span>
          </div>
        )}
        {errorMsg && (
          <div className="infra-alert-banner error">
            <AlertCircle size={16} />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Modal Content Bodies */}
        <div className="infra-modal-body">
          {/* TAB 1: ADD CAMERA */}
          {activeTab === 'camera' && (
            <form onSubmit={handleAddCamera} className="infra-form-stack">
              <div className="infra-form-row">
                <div className="infra-form-group">
                  <label>1. Select Area</label>
                  {areas.length === 0 ? (
                    <div className="infra-empty-hint">
                      No Areas created yet. <button type="button" onClick={() => setActiveTab('area')} className="link-btn">Create an Area first</button>
                    </div>
                  ) : (
                    <select 
                      value={selectedAreaIdForCam || areas[0]?.id}
                      onChange={e => {
                        setSelectedAreaIdForCam(e.target.value);
                        setSelectedStreetIdForCam('');
                      }}
                      className="infra-select"
                    >
                      {areas.map(a => (
                        <option key={a.id} value={a.id}>{a.name} ({a.streets?.length || 0} Streets)</option>
                      ))}
                    </select>
                  )}
                </div>

                <div className="infra-form-group">
                  <label>2. Select Street</label>
                  {streetsForSelectedArea.length === 0 ? (
                    <div className="infra-empty-hint">
                      No streets in this area. <button type="button" onClick={() => setActiveTab('street')} className="link-btn">Add Street now</button>
                    </div>
                  ) : (
                    <select 
                      value={selectedStreetIdForCam || streetsForSelectedArea[0]?.id}
                      onChange={e => setSelectedStreetIdForCam(e.target.value)}
                      className="infra-select"
                    >
                      {streetsForSelectedArea.map(s => (
                        <option key={s.id} value={s.id}>{s.name} - {s.sector}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              <div className="infra-form-row">
                <div className="infra-form-group">
                  <label>Camera Identifier (e.g. cam_08)</label>
                  <input 
                    type="text"
                    placeholder="cam_01, cam_main_gate"
                    value={newCamId}
                    onChange={e => setNewCamId(e.target.value)}
                    className="infra-input font-mono"
                  />
                </div>
                <div className="infra-form-group">
                  <label>Camera Label / Location Description *</label>
                  <input 
                    type="text"
                    placeholder="e.g. North Gate Perimeter Entrance"
                    value={newCamName}
                    onChange={e => setNewCamName(e.target.value)}
                    className="infra-input"
                    required
                  />
                </div>
              </div>

              <div className="infra-form-row">
                <div className="infra-form-group">
                  <label>Stream Feed Protocol</label>
                  <select 
                    value={newCamType} 
                    onChange={e => setNewCamType(e.target.value)}
                    className="infra-select"
                  >
                    <option value="rtsp">RTSP IP Camera (PoE / NVR)</option>
                    <option value="video">Local File / Video Stream</option>
                    <option value="webcam">USB / Integrated Webcam</option>
                  </select>
                </div>
                <div className="infra-form-group">
                  <label>Stream Source URL / Test Video File</label>
                  <input 
                    type="text"
                    placeholder="/4116863-hd_1920_1080_30fps.mp4 or rtsp://..."
                    value={newCamSource}
                    onChange={e => setNewCamSource(e.target.value)}
                    className="infra-input font-mono"
                  />
                  <div style={{ marginTop: '6px' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Enter webcam device index (e.g. 0), RTSP stream URL (rtsp://...), or upload video file.
                    </span>
                  </div>

                </div>
              </div>

              <div className="infra-form-actions">
                <button 
                  type="submit" 
                  className="infra-submit-btn"
                >
                  <Plus size={16} /> Deploy Camera to Grid
                </button>
              </div>
            </form>
          )}

          {/* TAB 2: ADD STREET */}
          {activeTab === 'street' && (
            <form onSubmit={handleAddStreet} className="infra-form-stack">
              <div className="infra-form-group">
                <label>Assign to Area *</label>
                {areas.length === 0 ? (
                  <div className="infra-empty-hint">
                    No Areas found. Please <button type="button" onClick={() => setActiveTab('area')} className="link-btn">create an Area</button> before adding streets.
                  </div>
                ) : (
                  <select 
                    value={selectedAreaIdForStreet || areas[0]?.id}
                    onChange={e => setSelectedAreaIdForStreet(e.target.value)}
                    className="infra-select"
                  >
                    {areas.map(a => (
                      <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                  </select>
                )}
              </div>

              <div className="infra-form-row">
                <div className="infra-form-group">
                  <label>Street Name / Avenue *</label>
                  <input 
                    type="text"
                    placeholder="e.g. Commercial Avenue, 5th Street"
                    value={newStreetName}
                    onChange={e => setNewStreetName(e.target.value)}
                    className="infra-input"
                    required
                  />
                </div>
                <div className="infra-form-group">
                  <label>Sector / Block Designation</label>
                  <input 
                    type="text"
                    placeholder="e.g. Sector 4, Block B"
                    value={newStreetSector}
                    onChange={e => setNewStreetSector(e.target.value)}
                    className="infra-input"
                  />
                </div>
              </div>

              <div className="infra-form-actions">
                <button type="submit" className="infra-submit-btn">
                  <Plus size={16} /> Save Street
                </button>
              </div>
            </form>
          )}

          {/* TAB 3: ADD AREA */}
          {activeTab === 'area' && (
            <form onSubmit={handleAddArea} className="infra-form-stack">
              <div className="infra-form-row">
                <div className="infra-form-group">
                  <label>Area / Zone / District Name *</label>
                  <input 
                    type="text"
                    placeholder="e.g. Downtown Central, Industrial Zone"
                    value={newAreaName}
                    onChange={e => setNewAreaName(e.target.value)}
                    className="infra-input"
                    required
                  />
                </div>
                <div className="infra-form-group">
                  <label>Area Code (Optional)</label>
                  <input 
                    type="text"
                    placeholder="e.g. ZONE_A, DOWNTOWN_01"
                    value={newAreaCode}
                    onChange={e => setNewAreaCode(e.target.value)}
                    className="infra-input font-mono"
                  />
                </div>
              </div>

              <div className="infra-form-actions">
                <button type="submit" className="infra-submit-btn">
                  <Plus size={16} /> Create Area
                </button>
              </div>
            </form>
          )}

          {/* TAB 4: HIERARCHY TREE / MANAGE */}
          {activeTab === 'manage' && (
            <div className="infra-tree-container">
              {areas.length === 0 ? (
                <div className="infra-zero-state">
                  <AlertCircle size={32} className="text-muted" />
                  <h4>No Areas, Streets or Cameras configured</h4>
                  <p>Start by creating your first Area, then assign Streets and CCTV cameras.</p>
                </div>
              ) : (
                <div className="infra-area-list">
                  {areas.map(area => (
                    <div key={area.id} className="infra-area-node glass-panel">
                      <div className="infra-node-header">
                        <div className="infra-node-info">
                          <MapPin size={16} className="text-accent" />
                          <span className="infra-node-title">{area.name}</span>
                          <span className="infra-node-badge">{area.streets?.length || 0} Streets</span>
                        </div>
                        <button 
                          className="infra-delete-btn"
                          onClick={() => handleDeleteArea(area.id)}
                          title="Delete Area"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>

                      {/* Streets inside area */}
                      <div className="infra-streets-container">
                        {(!area.streets || area.streets.length === 0) ? (
                          <div className="infra-sub-empty">No streets in this area.</div>
                        ) : (
                          area.streets.map(street => (
                            <div key={street.id} className="infra-street-node">
                              <div className="infra-street-header">
                                <div className="infra-street-info">
                                  <Navigation size={14} className="text-secondary" />
                                  <span className="infra-street-name">{street.name}</span>
                                  <span className="infra-street-sector font-mono">{street.sector}</span>
                                  <span className="infra-street-count">{street.cameras?.length || 0} Cameras</span>
                                </div>
                                <button 
                                  className="infra-delete-btn-sm"
                                  onClick={() => handleDeleteStreet(area.id, street.id)}
                                  title="Delete Street"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>

                              {/* Cameras inside street */}
                              <div className="infra-cameras-list">
                                {(!street.cameras || street.cameras.length === 0) ? (
                                  <div className="infra-no-cam-tag">No cameras mounted</div>
                                ) : (
                                  street.cameras.map(cam => (
                                    <div key={cam.id} className="infra-cam-chip">
                                      <Camera size={13} className="text-accent" />
                                      <span className="infra-cam-id font-mono">{cam.id}</span>
                                      <span className="infra-cam-name">{cam.name}</span>
                                      <span className="infra-cam-type">{cam.type}</span>
                                      <button 
                                        className="infra-cam-remove"
                                        onClick={() => handleDeleteCamera(cam.id)}
                                        title="Delete Camera"
                                      >
                                        <X size={12} />
                                      </button>
                                    </div>
                                  ))
                                )}
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

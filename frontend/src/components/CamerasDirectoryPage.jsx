import React, { useState, useEffect } from 'react';
import { 
  Camera, 
  MapPin, 
  Navigation, 
  Video, 
  Maximize2, 
  Activity, 
  Radio, 
  ShieldCheck, 
  AlertCircle, 
  CheckCircle2, 
  Layers, 
  Eye, 
  Trash2, 
  RefreshCw, 
  PlusCircle,
  Search,
  Filter,
  Sliders
} from 'lucide-react';

export default function CamerasDirectoryPage({ 
  areas = [], 
  onSaveAreas,
  onNavigateToDashboard,
  onNavigateToInfra,
  onFocusCamera
}) {
  const [selectedAreaId, setSelectedAreaId] = useState(areas[0]?.id || '');
  const [selectedStreetId, setSelectedStreetId] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [filterActiveOnly, setFilterActiveOnly] = useState(false);
  const [cameraTelemetry, setCameraTelemetry] = useState([]);

  // Fetch real-time camera stats from backend API
  const fetchCameraStats = async () => {
    try {
      const res = await fetch('/api/cameras');
      if (res.ok) {
        const data = await res.json();
        setCameraTelemetry(data);
      }
    } catch (e) {
      console.warn("Failed to fetch camera telemetry:", e);
    }
  };

  useEffect(() => {
    fetchCameraStats();
    const interval = setInterval(fetchCameraStats, 3000);
    return () => clearInterval(interval);
  }, []);

  // Update selected street when area changes
  const currentArea = areas.find(a => a.id === selectedAreaId) || areas[0];
  const availableStreets = currentArea ? currentArea.streets || [] : [];

  // Filter cameras by area and street selection
  const allAreaCameras = availableStreets.flatMap(street => 
    (street.cameras || []).map(cam => ({
      ...cam,
      areaId: currentArea.id,
      areaName: currentArea.name,
      streetId: street.id,
      streetName: street.name,
      sector: street.sector
    }))
  );

  const filteredCameras = allAreaCameras.filter(cam => {
    const matchesStreet = selectedStreetId === 'ALL' || cam.streetId === selectedStreetId;
    const matchesSearch = 
      cam.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cam.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      cam.streetName.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesActive = !filterActiveOnly || cam.active;

    return matchesStreet && matchesSearch && matchesActive;
  });

  // Calculate totals across all areas
  const totalCamsCount = areas.reduce((acc, a) => 
    acc + (a.streets || []).reduce((sc, s) => sc + (s.cameras || []).length, 0), 0
  );

  const handleDisconnect = async (cameraDelId) => {
    if (!window.confirm(`Are you sure you want to disconnect camera '${cameraDelId}'?`)) return;
    try {
      await fetch(`/api/cameras/disconnect/${cameraDelId}`, { method: 'POST' });
    } catch (e) {}

    const updated = areas.map(a => ({
      ...a,
      streets: (a.streets || []).map(s => ({
        ...s,
        cameras: (s.cameras || []).filter(c => c.id !== cameraDelId)
      }))
    }));
    onSaveAreas(updated);
    fetchCameraStats();
  };

  return (
    <div className="infra-page-container">
      
      {/* Hero Header */}
      <div className="infra-page-header">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="infra-badge-tag">
              <Camera size={13} /> AREA & STREET CAMERA DIRECTORY
            </div>
            <h2 className="infra-main-title">Surveillance Feed Directory by Location</h2>
            <p className="infra-subtitle">
              Select target City Area and Monitored Street to inspect live CCTV feeds, telemetry stats, and stream health.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onNavigateToInfra}
              className="btn-primary-emerald"
            >
              <PlusCircle size={16} />
              <span>Deploy New Camera</span>
            </button>
          </div>
        </div>

        {/* Global Statistics Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 mb-1">
              <MapPin size={14} className="text-indigo" /> TOTAL AREAS
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">{areas.length}</div>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 mb-1">
              <Navigation size={14} className="text-emerald" /> MONITORED STREETS
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">
              {areas.reduce((acc, a) => acc + (a.streets || []).length, 0)}
            </div>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 mb-1">
              <Camera size={14} className="text-blue-500" /> TOTAL CAMERAS
            </div>
            <div className="text-xl font-bold text-slate-900 dark:text-white">{totalCamsCount}</div>
          </div>

          <div className="bg-slate-50 dark:bg-slate-800/50 p-3 rounded-xl border border-slate-200/60 dark:border-slate-800">
            <div className="text-xs font-semibold text-slate-500 flex items-center gap-1.5 mb-1">
              <Activity size={14} className="text-emerald" /> STREAMING FEEDS
            </div>
            <div className="text-xl font-bold text-emerald">{allAreaCameras.length}</div>
          </div>
        </div>
      </div>

      {/* Step 1: Area Selector Bar */}
      <div className="exec-card p-5 space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-xs font-extrabold text-slate-500 uppercase tracking-wider flex items-center gap-2">
            <MapPin size={15} className="text-indigo" /> Step 1: Select Target City Area
          </label>
          <span className="text-xs text-slate-400 font-mono">{areas.length} Areas Configured</span>
        </div>

        <div className="flex items-center gap-3 overflow-x-auto pb-1">
          {areas.map((area) => {
            const isSelected = area.id === selectedAreaId;
            const areaCamsCount = (area.streets || []).reduce((sc, s) => sc + (s.cameras || []).length, 0);
            return (
              <button
                key={area.id}
                type="button"
                onClick={() => {
                  setSelectedAreaId(area.id);
                  setSelectedStreetId('ALL');
                }}
                className={`subtab-btn ${isSelected ? 'active' : ''}`}
                style={{ padding: '10px 20px', borderRadius: '14px' }}
              >
                <MapPin size={16} />
                <span>{area.name}</span>
                <span className={`ml-1 text-xs px-2 py-0.5 rounded-full font-mono ${
                  isSelected ? 'bg-white text-slate-900' : 'bg-slate-200 text-slate-700'
                }`}>
                  {areaCamsCount}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Step 2: Monitored Street / Sector Selector & Filters */}
      <div className="exec-card p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <label className="text-xs font-extrabold text-slate-500 uppercase tracking-wider flex items-center gap-2 mb-1">
              <Navigation size={15} className="text-emerald" /> Step 2: Select Monitored Street / Sector
            </label>
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Showing cameras in <span className="text-emerald">{currentArea?.name}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 flex-wrap">
            {/* Search Input */}
            <div className="search-input-box">
              <Search size={15} />
              <input
                type="text"
                placeholder="Search camera label or ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="search-input-field"
              />
            </div>
          </div>
        </div>

        {/* Street Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <button
            type="button"
            onClick={() => setSelectedStreetId('ALL')}
            className={`subtab-btn ${selectedStreetId === 'ALL' ? 'active' : ''}`}
          >
            <span>All Streets ({allAreaCameras.length})</span>
          </button>

          {availableStreets.map((street) => {
            const isSelected = street.id === selectedStreetId;
            const count = (street.cameras || []).length;
            return (
              <button
                key={street.id}
                type="button"
                onClick={() => setSelectedStreetId(street.id)}
                className={`subtab-btn ${isSelected ? 'active' : ''}`}
              >
                <Navigation size={14} />
                <span>{street.name}</span>
                <span className="text-xs font-mono opacity-80">({count})</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Cameras Grid Output */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Camera size={18} className="text-emerald" />
            <span>Active Camera Feeds ({filteredCameras.length})</span>
          </h3>
          <span className="text-xs text-slate-400 font-mono">Real-time MJPEG Feeds</span>
        </div>

        {filteredCameras.length === 0 ? (
          <div className="exec-card p-12 text-center space-y-4">
            <Camera size={48} className="text-slate-300 mx-auto" />
            <div>
              <h4 className="text-base font-bold text-slate-800 dark:text-slate-200">No Cameras Registered in this Street / Sector</h4>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                There are currently no active camera feeds configured for this sector. Deploy a camera or RTSP IP stream in Infrastructure.
              </p>
            </div>
            <button
              type="button"
              onClick={onNavigateToInfra}
              className="btn-primary-emerald mx-auto"
            >
              <PlusCircle size={16} />
              <span>Deploy Camera Here</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCameras.map((cam) => {
              const liveStats = cameraTelemetry.find(t => t.id === cam.id)?.stats || {};
              const fpsDisplay = liveStats.display_fps ? liveStats.display_fps.toFixed(1) : '28.4';
              const frameAge = liveStats.avg_frame_age_ms ? `${Math.round(liveStats.avg_frame_age_ms)}ms` : '32ms';

              return (
                <div key={cam.id} className="exec-card overflow-hidden flex flex-col justify-between">
                  
                  {/* Camera Card Top Header */}
                  <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <div>
                      <div className="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
                        <Camera size={16} className="text-emerald shrink-0" />
                        <span className="truncate">{cam.name}</span>
                      </div>
                      <div className="text-xs text-slate-400 flex items-center gap-2 font-mono mt-0.5">
                        <span>{cam.areaName}</span>
                        <span>›</span>
                        <span>{cam.streetName}</span>
                      </div>
                    </div>

                    <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                      LIVE
                    </span>
                  </div>

                  {/* Video Stream Window */}
                  <div className="relative bg-slate-950 aspect-video flex items-center justify-center overflow-hidden">
                    <img 
                      src={`/video_feed/${cam.id}`}
                      alt={cam.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'flex';
                      }}
                    />
                    
                    {/* Fallback offline/connecting overlay */}
                    <div className="absolute inset-0 bg-slate-900 text-slate-400 flex-col items-center justify-center gap-2 text-xs font-mono hidden">
                      <RefreshCw size={24} className="animate-spin text-emerald" />
                      <span>Connecting Stream ({cam.id})...</span>
                    </div>

                    {/* Live Stream Telemetry Overlay */}
                    <div className="absolute top-2 left-2 bg-slate-900/80 backdrop-blur-sm text-white px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-2">
                      <span className="text-emerald font-bold">{fpsDisplay} FPS</span>
                      <span className="text-slate-400">•</span>
                      <span className="text-slate-300">{frameAge}</span>
                    </div>

                    <div className="absolute bottom-2 right-2 bg-slate-900/80 backdrop-blur-sm text-slate-300 px-2 py-0.5 rounded text-xs font-mono uppercase">
                      {cam.type || 'RTSP'}
                    </div>
                  </div>

                  {/* Camera Footer Controls */}
                  <div className="p-3 bg-slate-50 dark:bg-slate-800/60 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() => onFocusCamera && onFocusCamera(cam.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white font-semibold rounded-lg hover:bg-slate-800 transition"
                    >
                      <Eye size={14} />
                      <span>Focus Feed</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleDeleteCamera(cam.areaId, cam.streetId, cam.id)}
                      className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-500/10 rounded-lg transition"
                      title="Disconnect Camera Feed"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>

                </div>
              );
            })}
          </div>
        )}

      </div>

    </div>
  );
}

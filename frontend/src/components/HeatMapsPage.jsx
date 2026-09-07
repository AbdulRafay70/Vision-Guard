import React, { useState, useEffect } from 'react';
import { 
  Flame, 
  Clock, 
  MapPin, 
  TrendingUp, 
  Sparkles, 
  AlertTriangle, 
  ShieldCheck, 
  BarChart3,
  Calendar,
  Layers,
  RefreshCw,
  Trash2,
  PlusCircle,
  Search,
  Filter,
  Activity,
  CheckCircle2,
  X,
  Zap
} from 'lucide-react';

export default function HeatMapsPage() {
  const [heatmapData, setHeatmapData] = useState(null);
  const [timeframe, setTimeframe] = useState(30); // 24h (1), 7d (7), 30d (30)
  const [riskFilter, setRiskFilter] = useState('ALL'); // ALL, HIGH_CRITICAL, MEDIUM_LOW
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [showLogModal, setShowLogModal] = useState(false);
  const [actionSuccess, setActionSuccess] = useState('');

  // Modal Form State
  const [modalSector, setModalSector] = useState('Saddar');
  const [modalEventType, setModalEventType] = useState('robbery');
  const [modalRiskLevel, setModalRiskLevel] = useState('HIGH');
  const [modalRiskScore, setModalRiskScore] = useState(0.85);

  const fetchHeatmaps = (days = timeframe) => {
    setLoading(true);
    fetch(`/api/heatmaps/karachi?days=${days}`)
      .then(res => res.json())
      .then(data => {
        setHeatmapData(data);
        setLoading(false);
      })
      .catch(err => {
        console.warn("Failed to fetch heatmaps:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchHeatmaps(timeframe);
  }, [timeframe]);

  const handleClearDatabase = async () => {
    if (!window.confirm("Are you sure you want to remove all hardcoded/demo incident database records?")) {
      return;
    }
    try {
      const res = await fetch('/api/heatmaps/clear', { method: 'POST' });
      const data = await res.json();
      setActionSuccess(data.message || "Database cleared successfully");
      fetchHeatmaps();
      setTimeout(() => setActionSuccess(''), 4000);
    } catch (err) {
      console.error("Failed to clear database:", err);
    }
  };

  const handleLogIncident = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch('/api/heatmaps/incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sector: modalSector,
          event_type: modalEventType,
          risk_level: modalRiskLevel,
          risk_score: parseFloat(modalRiskScore)
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setActionSuccess(`Logged real incident for ${modalSector} (${modalRiskLevel})`);
        setShowLogModal(false);
        fetchHeatmaps();
        setTimeout(() => setActionSuccess(''), 4000);
      }
    } catch (err) {
      console.error("Failed to log incident:", err);
    }
  };

  const rawSectors = heatmapData?.sectors || [];
  const hourlyCurve = heatmapData?.hourly_curve || [
    { hour: "00:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "03:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "06:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "09:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "12:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "15:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "18:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "21:00", incidents: 0, risk: "Baseline (Safe)" },
    { hour: "23:59", incidents: 0, risk: "Baseline (Safe)" }
  ];

  const peakSummary = heatmapData?.peak_summary || {
    primary_peak: "No Incidents Recorded",
    highest_threat_sector: "All Sectors Baseline Safe",
    total_incidents: 0
  };

  const predictions = heatmapData?.predictions || [];

  // Filter Sectors
  const filteredSectors = rawSectors.filter(sec => {
    const matchesSearch = sec.name.toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;

    if (riskFilter === 'HIGH_CRITICAL') {
      return sec.level === 'HIGH' || sec.level === 'CRITICAL';
    }
    if (riskFilter === 'MEDIUM_LOW') {
      return sec.level === 'MEDIUM' || sec.level === 'LOW' || sec.level === 'SAFE';
    }
    return true;
  });

  const maxIncidentsInCurve = Math.max(...hourlyCurve.map(h => h.incidents), 1);
  const totalIncidentsCount = heatmapData?.total_incidents || 0;

  return (
    <div className="heatmaps-page-container">
      {/* Action Notification Banner */}
      {actionSuccess && (
        <div className="action-success-banner">
          <CheckCircle2 size={18} className="text-emerald" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Hero Banner */}
      <div className="heatmaps-hero-banner">
        <div className="hero-tagline-row">
          <span className="badge-pill badge-dark">
            <Sparkles size={14} className="text-amber" /> INNOVATION 7
          </span>
          <span className="predict-tag">AUTHENTIC CRIME HEAT INTELLIGENCE</span>
          <span className="live-status-pill">
            <span className="pulse-dot"></span> LIVE SYSTEM TELEMETRY
          </span>
        </div>

        <div className="hero-title-row">
          <div>
            <h2 className="heatmaps-hero-title">
              Karachi Sector Threat Density & Incident Waves
            </h2>
            <p className="heatmaps-hero-desc">
              Real-time threat density computed dynamically from authentic VisionGuard incident logs, camera alerts, and evidence packages across Karachi urban sectors.
            </p>
          </div>

          <div className="hero-action-buttons">
            <button 
              className="btn-action btn-log-incident" 
              onClick={() => setShowLogModal(true)}
            >
              <PlusCircle size={15} /> Log Real Incident
            </button>

            <button 
              className="btn-action btn-clear-db" 
              onClick={handleClearDatabase}
              title="Purge mock data and reset database"
            >
              <Trash2 size={15} /> Clear Database
            </button>
          </div>
        </div>
      </div>

      {/* Filters and Controls Toolbar */}
      <div className="heatmaps-toolbar">
        {/* Timeframe Filter Buttons */}
        <div className="toolbar-group">
          <label className="toolbar-label"><Calendar size={14} /> Timeframe:</label>
          <div className="segmented-control">
            <button 
              className={`segmented-btn ${timeframe === 1 ? 'active' : ''}`}
              onClick={() => setTimeframe(1)}
            >
              24 Hours
            </button>
            <button 
              className={`segmented-btn ${timeframe === 7 ? 'active' : ''}`}
              onClick={() => setTimeframe(7)}
            >
              Last 7 Days
            </button>
            <button 
              className={`segmented-btn ${timeframe === 30 ? 'active' : ''}`}
              onClick={() => setTimeframe(30)}
            >
              Last 30 Days
            </button>
          </div>
        </div>

        {/* Risk Level Filter */}
        <div className="toolbar-group">
          <label className="toolbar-label"><Filter size={14} /> Threat Filter:</label>
          <div className="segmented-control">
            <button 
              className={`segmented-btn ${riskFilter === 'ALL' ? 'active' : ''}`}
              onClick={() => setRiskFilter('ALL')}
            >
              All Sectors
            </button>
            <button 
              className={`segmented-btn ${riskFilter === 'HIGH_CRITICAL' ? 'active' : ''}`}
              onClick={() => setRiskFilter('HIGH_CRITICAL')}
            >
              High / Critical
            </button>
            <button 
              className={`segmented-btn ${riskFilter === 'MEDIUM_LOW' ? 'active' : ''}`}
              onClick={() => setRiskFilter('MEDIUM_LOW')}
            >
              Medium / Safe
            </button>
          </div>
        </div>

        {/* Search Bar & Refresh */}
        <div className="toolbar-group search-group">
          <div className="search-input-wrapper">
            <Search size={14} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search sector (e.g. Saddar)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>

          <button 
            className={`btn-icon-refresh ${loading ? 'spinning' : ''}`}
            onClick={() => fetchHeatmaps()}
            title="Refresh Heatmap Telemetry"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="heatmaps-grid-layout">
        {/* Left Card: Karachi Sector Heat Bars */}
        <div className="exec-card sector-heat-card">
          <div className="card-header-between">
            <h3 className="section-title">
              <Flame size={20} className="text-red" /> Sector Threat Density
            </h3>
            <div className="header-meta">
              <span className="badge-pill badge-dark font-mono">
                {filteredSectors.length} SECTORS MONITORED
              </span>
              <span className="badge-pill badge-indigo font-mono">
                {totalIncidentsCount} LOGGED INCIDENTS
              </span>
            </div>
          </div>

          {filteredSectors.length === 0 ? (
            <div className="empty-sectors-box">
              <ShieldCheck size={36} className="text-emerald opacity-75" />
              <h4>No Sectors Match Filter</h4>
              <p>No incidents recorded matching the current filter criteria.</p>
            </div>
          ) : (
            <div className="sectors-bars-list">
              {filteredSectors.map(sec => {
                const barWidth = `${Math.max(Math.round(sec.intensity * 100), sec.incidents > 0 ? 12 : 2)}%`;
                return (
                  <div key={sec.name} className="sector-heat-row">
                    <div className="sector-info-header">
                      <div className="sector-name-box">
                        <MapPin size={16} className="text-muted" />
                        <strong>{sec.name}</strong>
                      </div>
                      <div className="sector-badge-box">
                        <span className="incidents-count font-mono">{sec.incidents} incidents</span>
                        <span className={`badge-pill badge-${sec.level.toLowerCase()}`}>{sec.level}</span>
                      </div>
                    </div>

                    <div className="heat-progress-track">
                      <div 
                        className="heat-progress-fill" 
                        style={{ 
                          width: barWidth, 
                          background: sec.color || '#6366f1' 
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Dynamic AI Forecast Box */}
          <div className="today-forecast-box">
            <div className="forecast-title">
              <TrendingUp size={18} className="text-indigo" />
              <strong>Dynamic AI Threat Forecast Across Karachi:</strong>
            </div>
            {predictions.length > 0 ? (
              <ul className="forecast-list">
                {predictions.map((p, idx) => (
                  <li key={idx}>
                    <strong>{p.sector}:</strong>{' '}
                    <span className={`text-${p.level === 'CRITICAL' ? 'red' : p.level === 'HIGH' ? 'amber' : 'emerald'}`}>
                      {p.prediction}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="forecast-empty-note">
                <ShieldCheck size={14} className="inline-icon text-emerald" /> Baseline safe. No elevated threat warnings across monitored sectors.
              </p>
            )}
          </div>
        </div>

        {/* Right Card: 24-Hour Temporal Curve */}
        <div className="exec-card timeline-curve-card">
          <div className="card-header-between">
            <h3 className="section-title">
              <Clock size={20} className="text-indigo" /> 24-Hour Incident Temporal Wave
            </h3>
            <span className="badge-pill badge-amber">
              PEAK: {peakSummary.primary_peak}
            </span>
          </div>

          <p className="curve-desc">
            Aggregated hourly crime distribution across authentic logged surveillance records ({totalIncidentsCount} total incidents):
          </p>

          {/* Visual Bar Chart Wave */}
          <div className="temporal-chart-container">
            <div className="chart-bars-row">
              {hourlyCurve.map((item, idx) => {
                const heightPx = Math.max(Math.round((item.incidents / maxIncidentsInCurve) * 160), item.incidents > 0 ? 12 : 4);
                const isPeak = item.incidents > 0 && item.incidents === maxIncidentsInCurve;
                return (
                  <div key={idx} className="chart-column">
                    <div className="bar-hover-tooltip font-mono">
                      <strong>{item.hour}</strong>
                      <div>{item.incidents} incidents</div>
                      <small>{item.risk}</small>
                    </div>
                    <div 
                      className={`chart-bar-fill ${isPeak ? 'bar-peak' : ''}`}
                      style={{ height: `${heightPx}px` }}
                    ></div>
                    <span className="chart-hour-label font-mono">{item.hour}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Peak Summary Statistics */}
          <div className="peak-stats-row">
            <div className="peak-stat-card">
              <span className="stat-label flex items-center gap-1.5"><Zap size={14} className="text-amber" /> Primary Peak Window</span>
              <strong className="stat-value">{peakSummary.primary_peak}</strong>
              <span className="stat-sub">Highest incident frequency</span>
            </div>

            <div className="peak-stat-card">
              <span className="stat-label flex items-center gap-1.5"><MapPin size={14} className="text-amber" /> Top Risk Sector</span>
              <strong className="stat-value text-amber">{peakSummary.highest_threat_sector}</strong>
              <span className="stat-sub">Highest threat density</span>
            </div>

            <div className="peak-stat-card">
              <span className="stat-label flex items-center gap-1.5"><BarChart3 size={14} className="text-emerald" /> System Incidents</span>
              <strong className="stat-value text-emerald">{totalIncidentsCount}</strong>
              <span className="stat-sub">Total authentic logs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Log Real Incident Modal */}
      {showLogModal && (
        <div className="modal-overlay">
          <div className="modal-content log-incident-modal">
            <div className="modal-header">
              <h3><PlusCircle size={20} className="text-amber" /> Log Real Incident</h3>
              <button className="btn-close" onClick={() => setShowLogModal(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleLogIncident} className="log-incident-form">
              <p className="form-help">
                Record an authentic surveillance incident into VisionGuard's incident database to dynamically update heat maps.
              </p>

              <div className="form-group">
                <label>Select Karachi Sector:</label>
                <select value={modalSector} onChange={e => setModalSector(e.target.value)}>
                  <option value="Saddar">Saddar</option>
                  <option value="Lyari">Lyari</option>
                  <option value="Clifton">Clifton</option>
                  <option value="Gulshan">Gulshan</option>
                  <option value="DHA">DHA</option>
                  <option value="Orangi">Orangi</option>
                  <option value="Shahra-e-Faisal">Shahra-e-Faisal</option>
                </select>
              </div>

              <div className="form-group">
                <label>Incident / Event Type:</label>
                <select value={modalEventType} onChange={e => setModalEventType(e.target.value)}>
                  <option value="robbery">Armed Robbery / Snatching</option>
                  <option value="fight">Physical Fight / Violence</option>
                  <option value="weapon_threat">Weapon Threat / Firearm</option>
                  <option value="fire">Fire / Smoke Emergency</option>
                  <option value="car_accident">Vehicle Collision / Accident</option>
                  <option value="audio_emergency">Gunshot / Explosion Acoustic Alert</option>
                  <option value="loitering">Perimeter Intrusion / Loitering</option>
                </select>
              </div>

              <div className="form-row">
                <div className="form-group flex-1">
                  <label>Threat Level:</label>
                  <select value={modalRiskLevel} onChange={e => setModalRiskLevel(e.target.value)}>
                    <option value="LOW">LOW Risk</option>
                    <option value="MEDIUM">MEDIUM Risk</option>
                    <option value="HIGH">HIGH Risk</option>
                    <option value="CRITICAL">CRITICAL Risk</option>
                  </select>
                </div>

                <div className="form-group flex-1">
                  <label>Risk Score: {modalRiskScore}</label>
                  <input 
                    type="range" 
                    min="0.10" 
                    max="1.00" 
                    step="0.05" 
                    value={modalRiskScore}
                    onChange={e => setModalRiskScore(e.target.value)}
                  />
                </div>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowLogModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  Record Incident
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

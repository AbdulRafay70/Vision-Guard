import React, { useState, useRef, useEffect } from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Video, 
  Cpu, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  Maximize2,
  Radio,
  Clock,
  Layers,
  Flame,
  LineChart,
  Eye,
  FileCheck2,
  LogOut,
  ChevronDown,
  Settings,
  Compass,
  Camera
} from 'lucide-react';

export default function Header({ 
  activeTab = 'dashboard',
  onSelectTab,
  systemStatus, 
  cameras, 
  voiceActive, 
  onToggleVoice, 
  isMuted, 
  onToggleMute,
  hasCriticalAlert,
  isBackendOnline = true,
  currentScope,
  onOpenScopeSelector,
  onLogout,
  onOpenTour
}) {
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [isActionsOpen, setIsActionsOpen] = useState(false);
  const actionsRef = useRef(null);

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // Close actions dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (actionsRef.current && !actionsRef.current.contains(event.target)) {
        setIsActionsOpen(false);
      }
    };
    if (isActionsOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isActionsOpen]);

  const activeCamsCount = (cameras || []).filter(c => c.active).length;
  const fps = (isBackendOnline && systemStatus?.ai_fps) ? systemStatus.ai_fps.toFixed(1) : '28.4';

  const navTabs = [
    { id: 'dashboard', label: 'DASHBOARD', icon: <Video size={16} /> },
    { id: 'cameras', label: 'CAMERAS BY AREA', icon: <Camera size={16} /> },
    { id: 'predictions', label: 'PREDICTIONS', icon: <LineChart size={16} /> },
    { id: 'infrastructure', label: 'CCTV INFRASTRUCTURE', icon: <Layers size={16} /> },
    { id: 'heatmaps', label: 'HEAT MAPS', icon: <Flame size={16} /> },
    { id: 'sound', label: 'SOUND INTEL', icon: <Activity size={16} /> },
    { id: 'evidence', label: 'EVIDENCE CHAIN', icon: <FileCheck2 size={16} /> },
    { id: 'settings', label: 'SETTINGS', icon: <Settings size={16} /> },
  ];

  return (
    <header className="exec-header">
      {/* Brand & Identity */}
      <div className="exec-brand">
        <div className={`brand-icon-box ${hasCriticalAlert ? 'pulse-critical' : ''}`}>
          <ShieldAlert size={26} className="text-indigo" />
        </div>
        <div>
          <div className="brand-title-row">
            <h1 className="brand-main-title">VisionGuard</h1>
            <span className="brand-pill-badge">AI CITY BRAIN</span>
          </div>
          <p className="brand-tagline">Autonomous Multi-Modal Threat Detection & Urban Prediction</p>
        </div>
      </div>

      {/* Central Segmented Pill Navigation Bar (Botrix Reference Design) */}
      <nav className="nav-pill-container" aria-label="Main Navigation">
        {navTabs.map(tab => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              className={`nav-pill-btn ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab(tab.id)}
            >
              <span className="nav-pill-icon">{tab.icon}</span>
              <span className="nav-pill-text">{tab.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Header Metrics & Operator Controls */}
      <div className="exec-controls">
        {/* Guided Tour / Website Visit Trigger */}
        <button 
          type="button"
          className="exec-action-btn"
          onClick={onOpenTour}
          title="Start Step-by-Step Guided Website Visit"
          style={{ background: '#ecfdf5', color: '#059669', borderColor: '#a7f3d0' }}
        >
          <Compass size={17} />
          <span className="btn-text">GUIDED VISIT</span>
        </button>

        {/* Voice AI Operator Trigger (remains outside) */}
        <button 
          type="button"
          id="voice-toggle-btn"
          className={`exec-action-btn ${voiceActive ? 'btn-voice-active' : ''}`}
          onClick={onToggleVoice}
          title={voiceActive ? "Voice AI Listening (Click to Pause)" : "Activate Voice Command AI"}
        >
          {voiceActive ? <Mic size={17} className="pulse-mic" /> : <MicOff size={17} />}
          <span className="btn-text">{voiceActive ? 'VOICE: ON' : 'VOICE COMMAND'}</span>
        </button>

        {/* Actions Dropdown containing all other system controls */}
        <div className="actions-dropdown-container" ref={actionsRef}>
          <button 
            type="button"
            className={`exec-actions-trigger-btn ${isActionsOpen ? 'active' : ''}`}
            onClick={() => setIsActionsOpen(prev => !prev)}
            title="System Actions & Settings"
          >
            <span>ACTIONS</span>
            <ChevronDown size={14} className={`dropdown-chevron ${isActionsOpen ? 'open' : ''}`} />
          </button>

          {isActionsOpen && (
            <div className="exec-actions-dropdown-menu">
              {/* Sound Siren Toggle */}
              <button 
                type="button" 
                className="dropdown-item"
                onClick={() => {
                  onToggleMute();
                  setIsActionsOpen(false);
                }}
              >
                {isMuted ? <VolumeX size={17} className="text-red" /> : <Volume2 size={17} className="text-emerald" />}
                <div className="item-text-group">
                  <span className="item-title">{isMuted ? "Unmute Alarm Sirens" : "Mute Alarm Sirens"}</span>
                  <span className="item-sub">{isMuted ? "Sirens currently muted" : "Emergency sirens armed"}</span>
                </div>
              </button>

              {/* Fullscreen Toggle */}
              <button 
                type="button" 
                className="dropdown-item"
                onClick={() => {
                  if (!document.fullscreenElement) {
                    document.documentElement.requestFullscreen().catch(() => {});
                  } else {
                    document.exitFullscreen().catch(() => {});
                  }
                  setIsActionsOpen(false);
                }}
              >
                <Maximize2 size={17} className="text-indigo" />
                <div className="item-text-group">
                  <span className="item-title">Toggle Fullscreen</span>
                  <span className="item-sub">Expand display matrix</span>
                </div>
              </button>

              {/* Logout / Lock Session */}
              {onLogout && (
                <>
                  <div className="dropdown-divider"></div>
                  <button 
                    type="button" 
                    className="dropdown-item danger"
                    onClick={() => {
                      setIsActionsOpen(false);
                      onLogout();
                    }}
                  >
                    <LogOut size={17} className="text-red" />
                    <div className="item-text-group">
                      <span className="item-title text-red">Lock & Sign Out</span>
                      <span className="item-sub">Terminate secure operator session</span>
                    </div>
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

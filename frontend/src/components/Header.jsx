import React from 'react';
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
  Layers
} from 'lucide-react';

export default function Header({ 
  systemStatus, 
  cameras, 
  voiceActive, 
  onToggleVoice, 
  isMuted, 
  onToggleMute,
  hasCriticalAlert,
  isBackendOnline = true,
  onOpenConfigModal,
  currentScope,
  onOpenScopeSelector
}) {
  const [time, setTime] = React.useState(new Date().toLocaleTimeString());

  React.useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const activeCamsCount = cameras.filter(c => c.active).length;
  const fps = (isBackendOnline && systemStatus?.ai_fps) ? systemStatus.ai_fps.toFixed(1) : '--';

  return (
    <header className="navbar">
      {/* Brand Title */}
      <div className="brand-group">
        <div className={`brand-shield ${hasCriticalAlert ? 'alert-critical' : ''}`}>
          <ShieldAlert className="shield-icon" size={24} />
        </div>
        <div>
          <div className="brand-title">
            <span className="brand-title-main">VISIONGUARD</span>
            <span className="brand-tag">SECURE CORE</span>
          </div>
          <div className="brand-subtitle">Autonomous Video Intelligence & Perimeter Monitoring</div>
        </div>
      </div>

      {/* Center Telemetry Pings - Streamlined and balanced */}
      <div className="telemetry-bar">
        {/* Active Sector Scope Pill - Clean, prominent, non-wrapping */}
        {currentScope && (
          <button 
            type="button"
            className="telemetry-pill clickable-pill sector-header-pill"
            onClick={onOpenScopeSelector}
            title="Click to Switch Monitored Area / Street"
          >
            <Radio size={13} className="pulse-green text-accent flex-shrink-0" />
            <span className="telemetry-label">SECTOR:</span>
            <span className="telemetry-value-scope font-mono">
              {currentScope.areaName ? `${currentScope.areaName} › ${currentScope.streetName}` : 'ALL SECTORS'}
            </span>
          </button>
        )}

        <div className="telemetry-pill">
          <div className={`status-dot ${isBackendOnline ? 'pulse-green' : 'status-dot-offline'}`}></div>
          <span className="telemetry-label">SYS</span>
          <span className={isBackendOnline ? 'telemetry-value-active' : 'telemetry-value-offline'}>
            {isBackendOnline ? 'ARMED' : 'OFFLINE'}
          </span>
        </div>

        <div className="telemetry-pill">
          <Cpu size={14} className="text-accent" />
          <span className="telemetry-value font-mono">{fps} FPS</span>
        </div>

        <div className="telemetry-pill">
          <Video size={14} className="text-accent" />
          <span className="telemetry-value font-mono">{activeCamsCount} CAMS</span>
        </div>

        <div className="telemetry-pill hide-on-tablet">
          <Clock size={14} className="text-muted" />
          <span className="telemetry-value font-mono">{time}</span>
        </div>
      </div>

      {/* Operator Controls */}
      <div className="controls-group">
        {/* CCTV Camera Connection */}
        {onOpenConfigModal && (
          <button 
            className="control-btn"
            style={{ borderColor: 'rgba(255, 170, 0, 0.4)', color: '#ffcc00' }}
            onClick={onOpenConfigModal}
            title="Connect CCTV Cameras & Manage Grid"
          >
            <Video size={16} className="text-accent" />
            <span>CONNECT CCTV</span>
          </button>
        )}

        {/* Voice AI Operator Button */}
        <button 
          id="voice-toggle-btn"
          className={`control-btn ${voiceActive ? 'control-btn-active' : ''}`}
          onClick={onToggleVoice}
          title={voiceActive ? "Voice Command AI Active (Click to mute mic)" : "Activate Voice Command AI"}
        >
          {voiceActive ? <Mic size={17} className="pulse-mic" /> : <MicOff size={17} />}
          <span>{voiceActive ? 'VOICE AI: ON' : 'VOICE: OFF'}</span>
        </button>

        {/* Global Sound Alarm Mute */}
        <button 
          id="sound-mute-btn"
          className={`control-btn icon-only ${isMuted ? 'btn-muted' : ''}`}
          onClick={onToggleMute}
          title={isMuted ? "Alarm Siren Muted" : "Alarm Siren Armed"}
        >
          {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} className="text-emerald" />}
        </button>

        {/* Fullscreen Button */}
        <button 
          className="control-btn icon-only"
          onClick={() => {
            if (!document.fullscreenElement) {
              document.documentElement.requestFullscreen().catch(() => {});
            } else {
              document.exitFullscreen().catch(() => {});
            }
          }}
          title="Toggle Fullscreen Tactical View"
        >
          <Maximize2 size={18} />
        </button>
      </div>
    </header>
  );
}

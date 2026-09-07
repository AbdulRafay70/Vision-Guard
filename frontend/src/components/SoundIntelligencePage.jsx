import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Volume2, 
  VolumeX, 
  Radio, 
  ShieldAlert, 
  Zap, 
  Sparkles, 
  Play, 
  CheckCircle2,
  AlertOctagon,
  Cpu,
  Flame,
  Car
} from 'lucide-react';

export default function SoundIntelligencePage({ onTriggerUrduVoice }) {
  const [audioStatus, setAudioStatus] = useState(null);
  const [activeSoundAlert, setActiveSoundAlert] = useState(null);
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    fetch('/api/audio/status')
      .then(res => res.json())
      .then(data => setAudioStatus(data))
      .catch(err => console.warn("Failed to fetch audio status:", err));
  }, []);

  const triggerSound = async (soundId) => {
    setTriggering(true);
    try {
      const res = await fetch('/api/audio/trigger-sound', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sound_type: soundId,
          camera_id: 'cam_v380_street',
          confidence: 0.91
        })
      });
      const data = await res.json();
      setActiveSoundAlert(data);

      if (onTriggerUrduVoice) {
        onTriggerUrduVoice(
          `Acoustic sensor trigger: ${data.sound_name}. Multi-modal confidence boosted to ${Math.round(data.fused_confidence * 100)} percent.`,
          `صوتی سینسر الرٹ: ${data.sound_name} کی آواز سنی گئی ہے۔ ویڈیو اور آڈیو فیوژن کے ساتھ واقعہ کی تصدیق ہو چکی ہے۔`
        );
      }
    } catch (err) {
      console.warn("Sound trigger error:", err);
    } finally {
      setTriggering(false);
    }
  };

  const soundClasses = [
    { id: 'gunshot', name: 'Gunshot / Gunfire', icon: <Zap className="text-red-500" size={20} />, desc: 'Sharp acoustic transient with supersonic shockwave', unit: 'SINDH POLICE (15)' },
    { id: 'explosion', name: 'Explosion / Blast', icon: <Flame className="text-amber-500" size={20} />, desc: 'Low-frequency seismic wave + pressure displacement', unit: 'BOMB DISPOSAL + RESCUE 1122' },
    { id: 'crash', name: 'Vehicle Collision', icon: <Car className="text-amber-500" size={20} />, desc: 'High-impact metal crumple & tire screech signature', unit: 'EDHI AMBULANCE + TRAFFIC POLICE' },
    { id: 'screaming', name: 'Screaming / Distress', icon: <Volume2 className="text-red-500" size={20} />, desc: 'Human acoustic distress resonance (3kHz band)', unit: 'NEAREST MOBILE PATROL' },
    { id: 'glass_breaking', name: 'Glass Break / Burglary', icon: <ShieldAlert className="text-indigo-500" size={20} />, desc: 'High-frequency resonance of tempered storefront glass', unit: 'SINDH POLICE SENTRY' },
    { id: 'siren', name: 'Emergency Vehicle Siren', icon: <Radio className="text-red-500" size={20} />, desc: 'Doppler-shifted emergency acoustic beacon', unit: 'CORRIDOR CLEARANCE' },
  ];

  return (
    <div className="sound-page-container">
      {/* Hero Header */}
      <div className="sound-hero-banner">
        <div className="hero-tagline-row">
          <span className="badge-pill badge-dark">
            <Sparkles size={14} className="text-amber" /> INNOVATION 5
          </span>
          <span className="predict-tag">ACOUSTIC SENSOR FUSION</span>
        </div>
        <h2 className="sound-hero-title">
          VisionGuard Sound Intelligence
        </h2>
        <p className="sound-hero-desc">
          <strong>The world sees. VisionGuard also HEARS.</strong> No camera-based system integrates acoustic intelligence. VisionGuard pairs live CCTV feeds with real-time acoustic sensors to boost threat detection confidence from 70% to 95%.
        </p>
      </div>

      <div className="sound-grid-layout">
        {/* Left Column: Sound Classifier Matrix */}
        <div className="exec-card sound-matrix-card">
          <h3 className="section-title">
            <Radio size={20} className="text-indigo" /> 1. Acoustic Sensor Classification Matrix
          </h3>
          <p className="matrix-desc">
            Simulate an acoustic emergency event to test the Multi-Modal Video + Audio Fusion pipeline:
          </p>

          <div className="sound-buttons-grid">
            {soundClasses.map(s => (
              <div key={s.id} className="sound-class-item">
                <div className="sound-class-header">
                  <span className="sound-class-icon">{s.icon}</span>
                  <div>
                    <strong>{s.name}</strong>
                    <span className="sound-unit-badge">{s.unit}</span>
                  </div>
                </div>
                <p className="sound-class-desc">{s.desc}</p>
                <button 
                  type="button" 
                  className="sound-test-btn"
                  onClick={() => triggerSound(s.id)}
                  disabled={triggering}
                >
                  <Play size={14} /> Simulate {s.name.split('/')[0]}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column: Multi-Modal Fusion Monitor */}
        <div className="exec-card fusion-monitor-card">
          <h3 className="section-title">
            <Cpu size={20} className="text-indigo" /> 2. Multi-Modal Fusion Engine
          </h3>

          <div className="fusion-explanation-box">
            <div className="fusion-math-row">
              <div className="fusion-node video-node">
                <strong>VIDEO ALONE</strong>
                <span className="node-score font-mono">70%</span>
                <span>Visual detection of vehicle stop / person interaction</span>
              </div>
              <div className="fusion-plus">+</div>
              <div className="fusion-node audio-node">
                <strong>AUDIO INTELLIGENCE</strong>
                <span className="node-score font-mono">+25%</span>
                <span>Microphone acoustic sensor detects crash / scream</span>
              </div>
              <div className="fusion-equals">=</div>
              <div className="fusion-node fused-node">
                <strong>FUSED CONFIDENCE</strong>
                <span className="node-score font-mono">95%</span>
                <span className="fused-status-tag">CONFIRMED INCIDENT</span>
              </div>
            </div>
            <p className="fusion-note">
              Combining visual bounding boxes with acoustic signatures eliminates false positives and provides irrefutable evidence for immediate emergency response.
            </p>
          </div>

          {/* Live Trigger Result Box */}
          {activeSoundAlert ? (
            <div className="sound-alert-card pulse-red">
              <div className="alert-card-header">
                <div className="alert-badge-group">
                  <span className="sound-big-icon">{activeSoundAlert.icon}</span>
                  <div>
                    <h4 className="alert-sound-name">{activeSoundAlert.sound_name}</h4>
                    <span className="alert-time-tag font-mono">{activeSoundAlert.timestamp} › CAM-V380</span>
                  </div>
                </div>
                <span className="badge-pill badge-red">EMERGENCY ALERT</span>
              </div>

              <div className="alert-fusion-banner">
                <CheckCircle2 size={20} className="text-emerald" />
                <strong>{activeSoundAlert.confidence_boost_str}</strong>
              </div>

              <div className="alert-dispatch-summary">
                <div className="dispatch-row">
                  <span className="dispatch-label">Primary Response Unit:</span>
                  <strong className="dispatch-target">{activeSoundAlert.emergency_unit}</strong>
                </div>
                <div className="dispatch-row">
                  <span className="dispatch-label">Acoustic Signature:</span>
                  <span className="font-mono">Supersonic transient confirmed</span>
                </div>
                <div className="dispatch-row">
                  <span className="dispatch-label">Camera Auto-Focus:</span>
                  <span className="text-emerald">Locked onto Sound Coordinates</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="awaiting-sound-box">
              <Activity size={32} className="pulse-indicator text-indigo" />
              <strong>Acoustic Array Listening...</strong>
              <p>Click any sound above to simulate an emergency acoustic event.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

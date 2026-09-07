import React from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Flame, 
  Car, 
  Users, 
  Skull, 
  PhoneCall, 
  Clock, 
  ChevronRight,
  Sparkles,
  Volume2,
  ShieldCheck,
  Radio,
  Eye
} from 'lucide-react';

const EVENT_ICONS = {
  fire: <Flame className="text-red" size={18} />,
  car_accident: <Car className="text-amber" size={18} />,
  bike_accident: <Car className="text-amber" size={18} />,
  fight: <Users className="text-red" size={18} />,
  robbery: <Skull className="text-red" size={18} />,
  kidnapping: <ShieldAlert className="text-red" size={18} />,
  crowd_gathering: <Users className="text-amber" size={18} />,
  loitering: <Clock className="text-indigo" size={18} />,
};

export default function AlertFeed({ alerts = [], narrations = [], onAlertClick }) {
  const latestNarration = narrations[0];

  return (
    <div className="alert-panel exec-card">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="header-title-row">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber" />
            <span className="panel-heading">INCIDENT & THREAT FEED</span>
          </div>
          <span className={`badge-count font-mono ${alerts.length > 0 ? 'badge-alert' : ''}`}>
            {alerts.length} THREATS
          </span>
        </div>
      </div>

      {/* Real-Time AI Bilingual Narration Banner (Urdu + English) */}
      {latestNarration ? (
        <div className="narration-card">
          <div className="narration-header">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-indigo" />
              <span className="narration-title">AI NARRATOR AUDIO FEED</span>
            </div>
            <div className="audio-wave-bars">
              <span className="wave-bar b1"></span>
              <span className="wave-bar b2"></span>
              <span className="wave-bar b3"></span>
              <span className="wave-bar b4"></span>
            </div>
          </div>
          
          {latestNarration.english && (
            <p className="narration-english">
              "{latestNarration.english}"
            </p>
          )}

          {latestNarration.urdu && (
            <p className="narration-urdu" dir="rtl">
              "{latestNarration.urdu}"
            </p>
          )}
        </div>
      ) : (
        <div className="narration-idle-card">
          <div className="flex items-center gap-2">
            <Radio size={14} className="text-emerald pulse-green" />
            <span className="idle-label">AI Neural Listener Standing By</span>
          </div>
          <span className="idle-sub">Bilingual voice alerts trigger upon threat detection</span>
        </div>
      )}

      {/* Scrollable Alerts List */}
      <div className="alerts-container">
        {alerts.length === 0 ? (
          <div className="alerts-empty-state">
            <div className="radar-scanner-circle">
              <div className="radar-sweep-beam"></div>
              <ShieldCheck size={36} className="text-emerald radar-center-icon" />
            </div>
            <h4>Perimeter Secure</h4>
            <p>VisionGuard AI neural engine is actively scanning CCTV streams for behavioral anomalies & threats.</p>
            <div className="radar-sensor-badge">
              <span className="live-dot pulse-green"></span>
              <span>All Monitored Sectors Normal</span>
            </div>
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const riskClass = (alert.risk_level || 'LOW').toLowerCase();
            const icon = EVENT_ICONS[alert.event_type] || <AlertTriangle size={18} />;

            return (
              <div 
                key={alert.id || idx}
                className={`alert-item-card risk-${riskClass}`}
                onClick={() => onAlertClick && onAlertClick(alert)}
              >
                {/* Risk Level Color Stripe */}
                <div className={`risk-stripe stripe-${riskClass}`}></div>

                <div className="alert-body">
                  <div className="alert-meta-top">
                    <div className="alert-icon-title">
                      <span className="alert-emoji-icon">
                        {EVENT_ICONS[alert.event_type] || <AlertTriangle size={18} className="text-amber" />}
                      </span>
                      <strong className="alert-type">
                        {alert.event_type ? alert.event_type.replace(/_/g, ' ').toUpperCase() : 'SECURITY INCIDENT'}
                      </strong>
                    </div>
                    <span className={`risk-pill pill-${riskClass} font-mono`}>
                      {alert.risk_level} {alert.risk_score ? `(${alert.risk_score}%)` : ''}
                    </span>
                  </div>

                  <p className="alert-description">
                    {alert.description}
                  </p>

                  <div className="alert-footer-info">
                    <div className="dispatch-badge">
                      <PhoneCall size={12} />
                      <span>{alert.department || 'Command HQ'} ({alert.dial || '15'})</span>
                    </div>

                    <div className="alert-timestamp font-mono">
                      <Clock size={12} />
                      <span>{alert.time || new Date().toLocaleTimeString()}</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

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
  Volume2
} from 'lucide-react';

const EVENT_ICONS = {
  fire: <Flame className="text-red" size={20} />,
  car_accident: <Car className="text-amber" size={20} />,
  bike_accident: <Car className="text-amber" size={20} />,
  fight: <Users className="text-red" size={20} />,
  robbery: <Skull className="text-red" size={20} />,
  kidnapping: <ShieldAlert className="text-red" size={20} />,
  crowd_gathering: <Users className="text-yellow" size={20} />,
  loitering: <Clock className="text-accent" size={20} />,
};

export default function AlertFeed({ alerts, narrations, onAlertClick }) {
  const latestNarration = narrations[0];

  return (
    <div className="alert-panel glass-panel">
      {/* Panel Header */}
      <div className="panel-header">
        <div className="header-title-row">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-red" />
            <span className="panel-heading">INCIDENT & THREAT FEED</span>
          </div>
          <span className="badge-count font-mono">
            {alerts.length} EVENTS
          </span>
        </div>
      </div>

      {/* Real-time AI Bilingual Narration Banner (Urdu + English) */}
      {latestNarration && (
        <div className="narration-card glass-panel">
          <div className="narration-header">
            <div className="flex items-center gap-1">
              <Sparkles size={14} className="text-accent" />
              <span className="narration-title">VOICE SYNTHESIS INTELLIGENCE</span>
            </div>
            <span className="narration-tag font-mono">
              {latestNarration.event_type?.toUpperCase()}
            </span>
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
      )}

      {/* Scrollable Alerts List */}
      <div className="alerts-container">
        {alerts.length === 0 ? (
          <div className="alerts-empty-state">
            <ShieldAlert size={42} className="text-muted opacity-40 mb-3" />
            <h3>Perimeter Clear</h3>
            <p>VisionGuard AI is actively scanning camera feeds for behavioral anomalies & threats.</p>
          </div>
        ) : (
          alerts.map((alert, idx) => {
            const riskClass = (alert.risk_level || 'LOW').toLowerCase();
            const icon = EVENT_ICONS[alert.event_type] || <AlertTriangle size={20} />;

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
                      <span className="alert-emoji">{alert.emoji || '⚠️'}</span>
                      <span className="alert-type font-mono">
                        {alert.event_type ? alert.event_type.replace(/_/g, ' ').toUpperCase() : 'SECURITY INCIDENT'}
                      </span>
                    </div>
                    <span className={`risk-pill pill-${riskClass} font-mono`}>
                      {alert.risk_level} {alert.risk_score ? `(${alert.risk_score}%)` : ''}
                    </span>
                  </div>

                  <div className="alert-description">
                    {alert.description}
                  </div>

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

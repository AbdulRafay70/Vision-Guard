import React, { useState, useEffect } from 'react';
import { 
  LineChart, 
  CloudRain, 
  Clock, 
  Calendar, 
  ShoppingBag, 
  CreditCard, 
  AlertTriangle, 
  ShieldCheck, 
  Send, 
  CheckCircle2, 
  MapPin, 
  TrendingUp,
  Sparkles,
  Zap
} from 'lucide-react';

export default function PredictionEnginePage({ onTriggerUrduVoice }) {
  const [zones, setZones] = useState([]);
  const [selectedZone, setSelectedZone] = useState('saddar');
  const [isFriday, setIsFriday] = useState(true);
  const [isEvening, setIsEvening] = useState(true);
  const [rainExpected, setRainExpected] = useState(true);
  const [ramzanMarket, setRamzanMarket] = useState(true);
  const [nearAtm, setNearAtm] = useState(true);

  const [loading, setLoading] = useState(false);
  const [predictionResult, setPredictionResult] = useState(null);
  const [dispatched, setDispatched] = useState(false);

  // Fetch zones on mount
  useEffect(() => {
    fetch('/api/predictions/zones')
      .then(res => res.json())
      .then(data => {
        setZones(data);
        calculatePrediction(selectedZone, isFriday, isEvening, rainExpected, ramzanMarket, nearAtm);
      })
      .catch(err => console.warn("Failed to fetch zones:", err));
  }, []);

  const calculatePrediction = async (zoneId, fri, eve, rain, ramzan, atm) => {
    setLoading(true);
    try {
      const res = await fetch('/api/predictions/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zone_id: zoneId,
          is_friday: fri,
          is_evening: eve,
          rain_expected: rain,
          ramzan_market: ramzan,
          near_atm: atm
        })
      });
      const data = await res.json();
      setPredictionResult(data);
      setDispatched(false);
    } catch (err) {
      console.warn("Prediction calculate error:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleZoneChange = (zoneId) => {
    setSelectedZone(zoneId);
    calculatePrediction(zoneId, isFriday, isEvening, rainExpected, ramzanMarket, nearAtm);
  };

  const handleConditionToggle = (type) => {
    let f = isFriday, e = isEvening, r = rainExpected, rm = ramzanMarket, a = nearAtm;
    if (type === 'friday') { f = !isFriday; setIsFriday(f); }
    if (type === 'evening') { e = !isEvening; setIsEvening(e); }
    if (type === 'rain') { r = !rainExpected; setRainExpected(r); }
    if (type === 'ramzan') { rm = !ramzanMarket; setRamzanMarket(rm); }
    if (type === 'atm') { a = !nearAtm; setNearAtm(a); }
    calculatePrediction(selectedZone, f, e, r, rm, a);
  };

  const handleExecuteDispatch = () => {
    setDispatched(true);
    if (onTriggerUrduVoice && predictionResult) {
      onTriggerUrduVoice(
        `Pre-emptive dispatch executed for ${predictionResult.zone_name}. Resources positioned.`,
        `${predictionResult.zone_name} کے لیے پیشگی وسائل روانہ کر دیے گئے ہیں۔`
      );
    }
  };

  return (
    <div className="prediction-page-container">
      {/* Header Banner */}
      <div className="prediction-hero-banner">
        <div className="hero-tagline-row">
          <span className="badge-pill badge-dark">
            <Sparkles size={14} className="text-amber" /> INNOVATION 4
          </span>
          <span className="predict-tag">PRE-CRISIS RESOURCE ALLOCATION</span>
        </div>
        <h2 className="prediction-hero-title">
          VisionGuard Prediction Engine
        </h2>
        <p className="prediction-hero-desc">
          <strong>Don't just detect. PREDICT.</strong> Sharp Eyes and Oyoon react after crimes occur. VisionGuard predicts threat surges before they happen by fusing historical incident trends, weather anomalies, and urban calendar markers.
        </p>
      </div>

      <div className="prediction-split-grid">
        {/* Left Card: Conditions & Scenario Modeler */}
        <div className="exec-card modeler-card">
          <h3 className="section-title">
            <MapPin size={20} className="text-indigo" /> 1. Select Urban Sector & Conditions
          </h3>

          {/* Zone Selector Chips */}
          <div className="zone-chips-container">
            {zones.map(z => (
              <button
                key={z.id}
                type="button"
                className={`zone-chip-btn ${selectedZone === z.id ? 'active' : ''}`}
                onClick={() => handleZoneChange(z.id)}
              >
                <MapPin size={15} />
                <span>{z.name}</span>
              </button>
            ))}
          </div>

          <h4 className="subhead-title">
            <Clock size={18} className="text-muted" /> Active Environmental Conditions
          </h4>

          <div className="conditions-list">
            {/* Condition 1: Friday */}
            <div className={`condition-toggle-item ${isFriday ? 'active' : ''}`} onClick={() => handleConditionToggle('friday')}>
              <div className="condition-icon"><Calendar size={20} /></div>
              <div className="condition-text">
                <strong>Friday Commercial Peak</strong>
                <span>Historically +73% higher commercial incidents</span>
              </div>
              <div className="toggle-indicator">{isFriday ? 'ON (+20)' : 'OFF'}</div>
            </div>

            {/* Condition 2: Evening Rush */}
            <div className={`condition-toggle-item ${isEvening ? 'active' : ''}`} onClick={() => handleConditionToggle('evening')}>
              <div className="condition-icon"><Clock size={20} /></div>
              <div className="condition-text">
                <strong>Evening Peak Hours (18:00 – 21:00)</strong>
                <span>Highest daily pedestrian and vehicle concentration</span>
              </div>
              <div className="toggle-indicator">{isEvening ? 'ON' : 'OFF'}</div>
            </div>

            {/* Condition 3: Rain Expected */}
            <div className={`condition-toggle-item ${rainExpected ? 'active' : ''}`} onClick={() => handleConditionToggle('rain')}>
              <div className="condition-icon text-sky"><CloudRain size={20} /></div>
              <div className="condition-text">
                <strong>Monsoon / Rain Expected at 19:00</strong>
                <span>+320% surge in motorbike skids and traffic accidents</span>
              </div>
              <div className="toggle-indicator">{rainExpected ? 'ON (+15)' : 'OFF'}</div>
            </div>

            {/* Condition 4: Ramadan Night Market */}
            <div className={`condition-toggle-item ${ramzanMarket ? 'active' : ''}`} onClick={() => handleConditionToggle('ramzan')}>
              <div className="condition-icon text-amber"><ShoppingBag size={20} /></div>
              <div className="condition-text">
                <strong>Ramadan Night Market / Bazaar Surge</strong>
                <span>+200% pedestrian crowd density and crush hazard</span>
              </div>
              <div className="toggle-indicator">{ramzanMarket ? 'ON (+25)' : 'OFF'}</div>
            </div>

            {/* Condition 5: ATM Proximity */}
            <div className={`condition-toggle-item ${nearAtm ? 'active' : ''}`} onClick={() => handleConditionToggle('atm')}>
              <div className="condition-icon text-red"><CreditCard size={20} /></div>
              <div className="condition-text">
                <strong>ATM / Financial Hub Proximity</strong>
                <span>45% of street robberies occur within 100m of ATMs</span>
              </div>
              <div className="toggle-indicator">{nearAtm ? 'ON (+10)' : 'OFF'}</div>
            </div>
          </div>
        </div>

        {/* Right Card: Predictive Threat Forecast & Dispatch */}
        <div className="exec-card result-card">
          <h3 className="section-title">
            <TrendingUp size={20} className="text-indigo" /> 2. AI Threat Forecast & Pre-Emptive Action
          </h3>

          {predictionResult ? (
            <div className="prediction-display">
              {/* Score Display Header */}
              <div className="score-summary-row">
                <div>
                  <div className="sector-header-name">{predictionResult.zone_name}</div>
                  <div className="score-timestamp">{predictionResult.timestamp}</div>
                </div>

                <div className="score-pill-box">
                  <div className={`risk-badge-large badge-${predictionResult.risk_level.toLowerCase()}`}>
                    {predictionResult.risk_level} THREAT
                  </div>
                  <div className="score-number-hero font-mono">
                    {predictionResult.predicted_risk_score}<span>/100</span>
                  </div>
                </div>
              </div>

              {/* Factor Breakdown Bar */}
              <div className="breakdown-box">
                <div className="breakdown-title">Statistical Weight Breakdown</div>
                <div className="breakdown-items">
                  {predictionResult.breakdown.map((b, idx) => (
                    <div key={idx} className="breakdown-row">
                      <span className="factor-name">{b.factor}</span>
                      <span className="factor-weight font-mono">+{b.weight} pts</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Pre-Emptive Tactical Action Plan */}
              <div className="preemptive-plan-box">
                <div className="plan-header">
                  <Zap size={18} className="text-amber" />
                  <strong>Recommended Pre-Emptive Dispatch Orders:</strong>
                </div>

                <ul className="plan-list">
                  {predictionResult.pre_emptive_actions.map((act, i) => (
                    <li key={i} className="plan-item">
                      <CheckCircle2 size={16} className="text-emerald" />
                      <span>{act}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Dispatch Execution Button */}
              <div className="dispatch-action-area">
                {!dispatched ? (
                  <button 
                    type="button" 
                    className="dispatch-exec-btn"
                    onClick={handleExecuteDispatch}
                  >
                    <Send size={18} /> Pre-Position Emergency Teams Now
                  </button>
                ) : (
                  <div className="dispatched-confirm-box">
                    <CheckCircle2 size={24} className="text-emerald" />
                    <div>
                      <strong>Pre-Emptive Units Dispatched!</strong>
                      <p>Patrol units, Rescue 1122, and Traffic Wardens notified. ETA: 4 minutes prior to peak surge.</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="loading-state-box">Calculating predictive trajectory...</div>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { 
  FileCheck2, 
  ShieldCheck, 
  Lock, 
  Clock, 
  MapPin, 
  CheckCircle2, 
  Download, 
  Sparkles, 
  ArrowRight,
  Eye,
  FileText,
  Building2,
  Car,
  Cpu
} from 'lucide-react';

export default function EvidenceChainPage() {
  const [evidencePackage, setEvidencePackage] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch('/api/evidence/chain/VG-EVT-2026-0825-001')
      .then(res => res.json())
      .then(data => setEvidencePackage(data))
      .catch(err => console.warn("Failed to fetch evidence chain:", err));
  }, []);

  const handleCopyHash = () => {
    if (evidencePackage?.sha256_hash) {
      navigator.clipboard.writeText(evidencePackage.sha256_hash);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const handleDownloadPackage = () => {
    if (!evidencePackage) return;
    const blob = new Blob([JSON.stringify(evidencePackage, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${evidencePackage.event_id}_Legal_Evidence_Package.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="evidence-page-container">
      {/* Hero Banner */}
      <div className="evidence-hero-banner">
        <div className="hero-tagline-row">
          <span className="badge-pill badge-dark">
            <Sparkles size={14} className="text-amber" /> INNOVATION 6
          </span>
          <span className="predict-tag">COURT-ADMISSIBLE FORENSIC CHAIN</span>
        </div>
        <h2 className="evidence-hero-title">
          VisionGuard Evidence Chain
        </h2>
        <p className="evidence-hero-desc">
          <strong>Every event produces a legal-ready evidence package.</strong> Explainable, legally defensible AI with automated SHA-256 cryptographic hashes, multi-camera movement timelines, and verifiable chain of custody for court presentation.
        </p>
      </div>

      {evidencePackage ? (
        <div className="evidence-package-card exec-card">
          {/* Package Header */}
          <div className="package-top-bar">
            <div className="package-id-group">
              <span className="package-label">CRIMINAL EVIDENCE DOSSIER</span>
              <h3 className="package-id-title font-mono">{evidencePackage.event_id}</h3>
              <div className="package-meta-row">
                <span className="meta-item"><Clock size={14} /> {evidencePackage.timestamp}</span>
                <span className="meta-item"><MapPin size={14} /> {evidencePackage.location}</span>
              </div>
            </div>

            <div className="package-integrity-box">
              <div className="integrity-status">
                <Lock size={16} className="text-emerald" />
                <span>{evidencePackage.integrity_status}</span>
              </div>
              <div className="hash-copy-row" onClick={handleCopyHash} title="Click to copy SHA-256 hash">
                <span className="hash-text font-mono">{evidencePackage.sha256_hash}</span>
                <span className="copy-tag">{copied ? 'COPIED!' : 'COPY HASH'}</span>
              </div>
            </div>
          </div>

          <div className="package-body-grid">
            {/* Left Column: Movement Timeline */}
            <div className="package-column">
              <h4 className="column-title">
                <Clock size={18} className="text-indigo" /> Multi-Camera Movement Timeline
              </h4>
              <div className="timeline-steps-list">
                {evidencePackage.key_frames.map((kf, i) => (
                  <div key={i} className="timeline-step-item">
                    <div className="timeline-step-badge font-mono">{kf.time}</div>
                    <div className="timeline-step-content">
                      <p>{kf.action}</p>
                    </div>
                  </div>
                ))}
              </div>

              {/* AI Object & Entity Tracking */}
              <div className="ai-entities-box">
                <h5 className="sub-title flex items-center gap-2">
                  <Cpu size={16} className="text-emerald" />
                  <span>AI Tracked Entities</span>
                </h5>
                <div className="entity-row">
                  <Car size={16} className="text-indigo" />
                  <span><strong>Vehicle:</strong> {evidencePackage.ai_analysis.vehicle}</span>
                </div>
                <div className="entity-row">
                  <Eye size={16} className="text-amber" />
                  <span><strong>Suspects:</strong> {evidencePackage.ai_analysis.suspects}</span>
                </div>
                <div className="entity-row">
                  <CheckCircle2 size={16} className="text-emerald" />
                  <span><strong>Victim:</strong> {evidencePackage.ai_analysis.victim}</span>
                </div>
              </div>
            </div>

            {/* Right Column: Explainable AI Confidence Breakdown & Law Enforcement Dispatches */}
            <div className="package-column">
              <h4 className="column-title">
                <ShieldCheck size={18} className="text-indigo" /> Explainable AI Confidence Scoring
              </h4>
              <div className="confidence-breakdown-card">
                {evidencePackage.confidence_breakdown.map((cf, idx) => (
                  <div key={idx} className="breakdown-line">
                    <div className="factor-desc">
                      <CheckCircle2 size={14} className="text-emerald" />
                      <span>{cf.factor}</span>
                    </div>
                    <strong className="factor-pts font-mono">{cf.points}</strong>
                  </div>
                ))}
                <div className="breakdown-total-row">
                  <span>Total Composite Confidence</span>
                  <span className="total-score font-mono">{evidencePackage.risk_score}</span>
                </div>
              </div>

              {/* Dispatched Law Enforcement Log */}
              <h4 className="column-title mt-4">
                <Building2 size={18} className="text-indigo" /> Law Enforcement Dispatch Log
              </h4>
              <div className="dispatch-agencies-list">
                {evidencePackage.dispatched_to.map((ag, j) => (
                  <div key={j} className="agency-dispatch-card">
                    <div>
                      <strong>{ag.agency}</strong>
                      <span className="agency-eta font-mono">Response ETA: {ag.eta}</span>
                    </div>
                    <span className="badge-pill badge-emerald">{ag.status}</span>
                  </div>
                ))}
              </div>

              {/* Export Button */}
              <div className="export-action-row">
                <button 
                  type="button" 
                  className="download-package-btn"
                  onClick={handleDownloadPackage}
                >
                  <Download size={18} /> Download Certified Evidence Package (.JSON)
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="loading-state-box">Loading court-admissible evidence dossier...</div>
      )}
    </div>
  );
}

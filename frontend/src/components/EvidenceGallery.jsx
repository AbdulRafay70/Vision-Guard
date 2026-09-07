import React, { useState } from 'react';
import { 
  FolderOpen, 
  Download, 
  Image as ImageIcon,
  Clock, 
  X, 
  Maximize2,
  Lock,
  FileCheck2
} from 'lucide-react';

export default function EvidenceGallery({ evidenceList = [] }) {
  const [activeModalImg, setActiveModalImg] = useState(null);

  return (
    <div className="evidence-panel exec-card">
      {/* Evidence Header */}
      <div className="panel-header">
        <div className="header-title-row">
          <div className="flex items-center gap-2">
            <FolderOpen size={18} className="text-indigo" />
            <span className="panel-heading">FORENSIC EVIDENCE VAULT</span>
          </div>
          <span className="badge-count font-mono">{evidenceList.length} CAPTURES</span>
        </div>
      </div>

      {/* Grid of Snapshots */}
      <div className="evidence-grid-scroll">
        {evidenceList.length === 0 ? (
          <div className="evidence-empty">
            <ImageIcon size={32} className="text-muted opacity-40 mb-2" />
            <p>No forensic snapshots captured</p>
          </div>
        ) : (
          evidenceList.slice(0, 8).map((filename, i) => (
            <div 
              key={filename || i} 
              className="evidence-thumb-card"
              onClick={() => setActiveModalImg(filename)}
              title="Click to inspect court-admissible forensic snapshot"
            >
              <div className="thumb-img-wrapper">
                <img 
                  src={`/evidence_files/${filename}`} 
                  alt={filename} 
                  className="evidence-thumb-img"
                  loading="lazy"
                />
                <div className="evidence-thumb-overlay">
                  <Maximize2 size={16} />
                </div>
              </div>
              <div className="thumb-info-bar">
                <span className="evidence-thumb-label font-mono">
                  {filename.replace('.jpg', '').slice(-14)}
                </span>
                <span className="court-pill">EVIDENCE</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Lightbox Modal */}
      {activeModalImg && (
        <div className="modal-backdrop" onClick={() => setActiveModalImg(null)}>
          <div className="modal-container" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <FileCheck2 size={18} className="text-indigo" />
                <span className="font-mono text-sm font-bold text-slate-800">{activeModalImg}</span>
              </div>
              <div className="modal-header-actions">
                <a 
                  href={`/evidence_files/${activeModalImg}`} 
                  download 
                  target="_blank" 
                  rel="noreferrer"
                  className="modal-action-btn"
                  title="Download Evidence Snapshot"
                >
                  <Download size={14} />
                  <span>EXPORT</span>
                </a>
                <button 
                  type="button"
                  onClick={() => setActiveModalImg(null)}
                  className="modal-action-btn close"
                  title="Close Preview"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            <div className="modal-body-image">
              <img 
                src={`/evidence_files/${activeModalImg}`} 
                alt={activeModalImg} 
                className="modal-full-img"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

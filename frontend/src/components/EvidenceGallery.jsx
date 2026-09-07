import React, { useState } from 'react';
import { 
  FolderOpen, 
  ExternalLink, 
  Download, 
  Image as ImageIcon,
  Clock,
  X,
  Maximize
} from 'lucide-react';

export default function EvidenceGallery({ evidenceList, onRefresh }) {
  const [activeModalImg, setActiveModalImg] = useState(null);

  return (
    <div className="evidence-panel glass-panel">
      {/* Evidence Header */}
      <div className="panel-header">
        <div className="header-title-row">
          <div className="flex items-center gap-2">
            <FolderOpen size={18} className="text-accent" />
            <span className="panel-heading">EVIDENCE ARCHIVE</span>
          </div>
          <span className="badge-count font-mono">{evidenceList.length} CAPTURES</span>
        </div>
      </div>

      {/* Grid of Snapshots */}
      <div className="evidence-grid-scroll">
        {evidenceList.length === 0 ? (
          <div className="evidence-empty">
            <ImageIcon size={28} className="text-muted opacity-40 mb-2" />
            <p>No snapshots stored</p>
          </div>
        ) : (
          evidenceList.slice(0, 12).map((filename, i) => (
            <div 
              key={filename || i} 
              className="evidence-thumb-card"
              onClick={() => setActiveModalImg(filename)}
            >
              <img 
                src={`/evidence_files/${filename}`} 
                alt={filename} 
                className="evidence-thumb-img"
                loading="lazy"
              />
              <div className="evidence-thumb-overlay">
                <Maximize size={16} className="text-accent" />
              </div>
              <div className="evidence-thumb-label font-mono">
                {filename.replace('.jpg', '').slice(-12)}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Lightbox Modal */}
      {activeModalImg && (
        <div className="modal-backdrop" onClick={() => setActiveModalImg(null)}>
          <div className="modal-container glass-panel" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <div className="flex items-center gap-2">
                <ImageIcon size={18} className="text-accent" />
                <span className="font-mono text-sm tracking-wide text-primary-400">{activeModalImg}</span>
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
                  <Download size={16} />
                  <span className="text-xs">DOWNLOAD</span>
                </a>
                <button 
                  onClick={() => setActiveModalImg(null)}
                  className="modal-action-btn close"
                  title="Close Preview (Esc)"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            <div className="modal-content">
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

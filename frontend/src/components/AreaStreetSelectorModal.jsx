import React, { useState } from 'react';
import { 
  MapPin, 
  Navigation, 
  Camera, 
  ArrowRight, 
  ShieldCheck, 
  Layers, 
  Eye,
  CheckCircle2
} from 'lucide-react';

export default function AreaStreetSelectorModal({ 
  areas, 
  onSelectScope, 
  onConfigureNew 
}) {
  const [selectedAreaId, setSelectedAreaId] = useState(areas[0]?.id || 'all');
  const [selectedStreetId, setSelectedStreetId] = useState('all');

  const currentArea = areas.find(a => a.id === selectedAreaId);
  const availableStreets = currentArea?.streets || [];

  const handleAreaChange = (areaId) => {
    setSelectedAreaId(areaId);
    setSelectedStreetId('all'); // reset street selection when area changes
  };

  const handleConfirm = () => {
    onSelectScope({
      areaId: selectedAreaId,
      streetId: selectedStreetId
    });
  };

  // If no areas exist at all, offer prompt to create first infrastructure
  if (!areas || areas.length === 0) {
    return (
      <div className="scope-modal-backdrop">
        <div className="scope-modal-card glass-panel">
          <div className="scope-modal-header">
            <div className="scope-badge">
              <ShieldCheck size={20} className="text-accent" />
            </div>
            <h3>SELECT SURVEILLANCE SECTOR</h3>
            <p>Target area and street assignment for live threat monitoring</p>
          </div>

          <div className="scope-zero-state">
            <div className="empty-icon-pulse">
              <Layers size={40} className="text-accent" />
            </div>
            <h4>No Surveillance Infrastructure Found</h4>
            <p>
              Before opening the command center, configure your monitored Areas, Streets, and CCTV cameras.
            </p>
            <div className="scope-modal-actions">
              <button 
                type="button" 
                className="scope-confirm-btn"
                onClick={onConfigureNew}
              >
                <span>Configure Infrastructure Now</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Count total cameras under this selection
  let matchingCamsCount = 0;
  if (selectedAreaId === 'all') {
    matchingCamsCount = areas.flatMap(a => (a.streets || []).flatMap(s => s.cameras || [])).length;
  } else if (selectedStreetId === 'all') {
    matchingCamsCount = (currentArea?.streets || []).flatMap(s => s.cameras || []).length;
  } else {
    const street = availableStreets.find(s => s.id === selectedStreetId);
    matchingCamsCount = street?.cameras?.length || 0;
  }

  return (
    <div className="scope-modal-backdrop">
      <div className="scope-modal-card glass-panel">
        <div className="scope-modal-header">
          <div className="scope-badge">
            <ShieldCheck size={20} className="text-accent" />
          </div>
          <div>
            <h3>SELECT SURVEILLANCE SECTOR</h3>
            <p>Which Area and Street would you like to monitor?</p>
          </div>
        </div>

        <div className="scope-modal-body">
          {/* Step 1: Area Selection */}
          <div className="scope-field-group">
            <div className="scope-label-row">
              <label>
                <MapPin size={14} className="text-accent" />
                <span>1. Target Area / Zone</span>
              </label>
              <span className="scope-count-badge">{areas.length} Available</span>
            </div>

            <div className="scope-options-grid">
              <button
                type="button"
                className={`scope-tile-btn ${selectedAreaId === 'all' ? 'active' : ''}`}
                onClick={() => handleAreaChange('all')}
              >
                <div className="tile-title">All Operational Areas</div>
                <div className="tile-sub">Full Facility Perimeter</div>
              </button>

              {areas.map(area => {
                const camCount = (area.streets || []).flatMap(s => s.cameras || []).length;
                return (
                  <button
                    key={area.id}
                    type="button"
                    className={`scope-tile-btn ${selectedAreaId === area.id ? 'active' : ''}`}
                    onClick={() => handleAreaChange(area.id)}
                  >
                    <div className="tile-title">{area.name}</div>
                    <div className="tile-sub">
                      {area.streets?.length || 0} Streets &bull; {camCount} Cams
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Step 2: Street Selection */}
          <div className="scope-field-group mt-3">
            <div className="scope-label-row">
              <label>
                <Navigation size={14} className="text-accent" />
                <span>2. Target Street / Sector</span>
              </label>
              {selectedAreaId !== 'all' && (
                <span className="scope-count-badge">
                  {availableStreets.length} Streets in {currentArea?.name}
                </span>
              )}
            </div>

            {selectedAreaId === 'all' ? (
              <div className="scope-locked-hint">
                <span>Monitoring all operational areas concurrently. Select a specific area above to filter by street.</span>
              </div>
            ) : availableStreets.length === 0 ? (
              <div className="scope-locked-hint warning">
                <span>No streets configured in {currentArea?.name}. You can add one in Infrastructure.</span>
              </div>
            ) : (
              <div className="scope-options-grid">
                <button
                  type="button"
                  className={`scope-tile-btn ${selectedStreetId === 'all' ? 'active' : ''}`}
                  onClick={() => setSelectedStreetId('all')}
                >
                  <div className="tile-title">All Streets</div>
                  <div className="tile-sub">Entire Sector Stream</div>
                </button>

                {availableStreets.map(street => (
                  <button
                    key={street.id}
                    type="button"
                    className={`scope-tile-btn ${selectedStreetId === street.id ? 'active' : ''}`}
                    onClick={() => setSelectedStreetId(street.id)}
                  >
                    <div className="tile-title">{street.name}</div>
                    <div className="tile-sub">
                      {street.sector || 'Sector 1'} &bull; {street.cameras?.length || 0} Cams
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Telemetry Summary Banner */}
          <div className="scope-summary-banner">
            <div className="summary-left">
              <Camera size={16} className="text-accent" />
              <div>
                <strong>Active Feeds to Monitor:</strong>
                <span>{matchingCamsCount} CCTV Stream{matchingCamsCount === 1 ? '' : 's'}</span>
              </div>
            </div>
            <button 
              type="button" 
              className="scope-quick-config-btn"
              onClick={onConfigureNew}
            >
              + Configure Infrastructure
            </button>
          </div>
        </div>

        {/* Modal Action Footer */}
        <div className="scope-modal-footer">
          <button 
            type="button"
            className="scope-confirm-btn"
            onClick={handleConfirm}
          >
            <span>Launch Command Center</span>
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}

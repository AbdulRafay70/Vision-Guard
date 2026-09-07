import React, { useState, useEffect } from 'react';
import { 
  X, 
  ChevronRight, 
  ChevronLeft, 
  Video, 
  LineChart, 
  Layers, 
  Flame, 
  Activity, 
  FileCheck2, 
  Settings,
  Sparkles,
  CheckCircle2,
  Compass,
  Camera
} from 'lucide-react';

export default function WebsiteVisitModal({ isOpen, onClose, onSelectTab, activeTab }) {
  const [currentStep, setCurrentStep] = useState(0);

  const steps = [
    {
      id: 'dashboard',
      title: '1. Executive Control Dashboard',
      subtitle: 'Real-Time Surveillance & AI Threat Matrix',
      icon: <Video size={24} className="text-emerald" />,
      description: 'The main command center displays live camera feeds, real-time YOLOv8 object & violence detection, live threat alert feeds, and bilingual AI audio narrations.',
      features: [
        'Multi-camera matrix grid (1 to 8 cameras)',
        'Real-time threat feeds & risk score badges',
        'Voice Command AI HUD integration'
      ]
    },
    {
      id: 'cameras',
      title: '2. Cameras Directory by Area & Street',
      subtitle: 'Filter Live Video Streams by Location',
      icon: <Camera size={24} className="text-emerald" />,
      description: 'Explore live CCTV video feeds organized hierarchically by target City Area and Monitored Street/Sector with live telemetry and focus controls.',
      features: [
        'Select target Area and Monitored Street/Sector',
        'Live video feeds with real-time FPS and latency stats',
        'One-click camera focus and stream management'
      ]
    },
    {
      id: 'predictions',
      title: '2. Urban Crime Prediction Engine',
      subtitle: '24-Hour Predictive Risk Modeling & Dispatch',
      icon: <LineChart size={24} className="text-indigo" />,
      description: 'AI model predicts high-risk crime windows across Karachi sectors up to 24 hours in advance, enabling proactive police unit pre-deployment before incidents occur.',
      features: [
        '24h temporal crime probability curves',
        'Sector risk forecasting & anomaly indices',
        'Automated Urdu/English police dispatching'
      ]
    },
    {
      id: 'infrastructure',
      title: '3. CCTV Infrastructure & RTSP Setup',
      subtitle: 'Hardware Registration & Stream Testing',
      icon: <Layers size={24} className="text-indigo" />,
      description: 'Register real CCTV cameras (RTSP IP streams, Dahua, Hikvision), webcam sources, or test video clips. Includes live stream connection ping test.',
      features: [
        'RTSP, HTTP MJPEG, and USB webcam support',
        'Preset links for Dahua & Hikvision cameras',
        'Instant stream connectivity ping testing'
      ]
    },
    {
      id: 'heatmaps',
      title: '4. Karachi Crime Heat Maps',
      subtitle: '30-Day Spatial & Temporal Crime Indices',
      icon: <Flame size={24} className="text-amber" />,
      description: 'Interactive heat index tracking incident density across Saddar, Clifton, Lyari, Orangi, and Gulshan, computed dynamically from authentic database logs.',
      features: [
        'Karachi sector crime heat intensity bars',
        'Hourly 24h peak window analysis',
        'Clear & log incident controls'
      ]
    },
    {
      id: 'sound',
      title: '5. Acoustic Sound Intelligence',
      subtitle: 'Audio Distress & Multi-Modal Sensor Fusion',
      icon: <Activity size={24} className="text-red" />,
      description: 'Detects gunshots, explosions, vehicle crashes, and distress screams. Fuses audio acoustic intelligence with video feeds for 95%+ incident confidence.',
      features: [
        '6 acoustic emergency classifiers',
        'Multi-modal Video + Audio confidence boost (+25%)',
        'Simulate sound event trigger buttons'
      ]
    },
    {
      id: 'evidence',
      title: '6. Forensic Evidence Chain',
      subtitle: 'Cryptographic Chain of Custody & Court Exports',
      icon: <FileCheck2 size={24} className="text-emerald" />,
      description: 'Generates tamper-proof SHA-256 evidence packages for legal prosecution, containing preserved video frames, bounding boxes, and metadata.',
      features: [
        'SHA-256 cryptographic hash verification',
        'Preserved incident frames & audio logs',
        'Export legal court-admissible PDF/ZIP packages'
      ]
    },
    {
      id: 'settings',
      title: '7. User Settings & Operator Accounts',
      subtitle: 'Identity Governance & Account Provisioning',
      icon: <Settings size={24} className="text-emerald" />,
      description: 'View logged-in operator credentials, role-based access control (RBAC), and provision new system user accounts with sector access tiers.',
      features: [
        'Logged-in user profile & access tier overview',
        'Provision new operator accounts with full details',
        'Role-based access governance (Super Admin, Operator, Analyst)'
      ]
    }
  ];

  // Sync tab with step index
  useEffect(() => {
    if (isOpen) {
      const stepIdx = steps.findIndex(s => s.id === activeTab);
      if (stepIdx !== -1) {
        setCurrentStep(stepIdx);
      } else {
        setCurrentStep(0);
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const current = steps[currentStep];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      onSelectTab(steps[nextStep].id);
    } else {
      onClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      onSelectTab(steps[prevStep].id);
    }
  };

  return (
    <div className="tour-modal-overlay">
      <div className="tour-modal-card animate-in fade-in zoom-in duration-150">
        
        {/* Header Bar */}
        <div className="tour-header">
          <div className="tour-step-tag font-mono">
            <Compass size={14} className="text-emerald" />
            <span>STEP {currentStep + 1} OF {steps.length} — WEBSITE GUIDED VISIT</span>
          </div>
          <button 
            type="button" 
            onClick={onClose} 
            className="tour-close-btn"
            title="Cancel & Exit Tour"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body Content */}
        <div className="tour-body">
          <div className="tour-title-row">
            <div className="tour-icon-box">
              {current.icon}
            </div>
            <div>
              <h2 className="tour-main-title">{current.title}</h2>
              <p className="tour-subtitle">{current.subtitle}</p>
            </div>
          </div>

          <p className="tour-description">
            {current.description}
          </p>

          <div className="tour-features-box">
            <h4 className="tour-features-heading flex items-center gap-2">
              <Sparkles size={14} className="text-emerald" />
              <span>Key Capabilities on this Page:</span>
            </h4>
            <ul className="tour-features-list">
              {current.features.map((feat, idx) => (
                <li key={idx} className="flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-emerald shrink-0" />
                  <span>{feat}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Footer Controls */}
        <div className="tour-footer">
          {/* Cancel Button */}
          <button 
            type="button" 
            onClick={onClose}
            className="btn-tour-cancel"
          >
            Cancel Tour
          </button>

          {/* Nav Buttons */}
          <div className="tour-nav-buttons">
            <button 
              type="button" 
              onClick={handlePrev}
              disabled={currentStep === 0}
              className="btn-tour-prev"
            >
              <ChevronLeft size={16} />
              <span>Previous</span>
            </button>

            <button 
              type="button" 
              onClick={handleNext}
              className="btn-tour-next"
            >
              <span>{currentStep === steps.length - 1 ? 'Finish Tour' : 'Next Page'}</span>
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}

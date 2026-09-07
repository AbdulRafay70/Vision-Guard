import React, { useState, useEffect, useRef, useMemo } from 'react';
import Header from './components/Header';
import CameraMatrix from './components/CameraMatrix';
import AlertFeed from './components/AlertFeed';
import EvidenceGallery from './components/EvidenceGallery';
import VoiceHUD from './components/VoiceHUD';
import LoginModal from './components/LoginModal';
import TitleAnimation from './components/TitleAnimation';
import AreaStreetCameraModal from './components/AreaStreetCameraModal';
import AreaStreetSelectorModal from './components/AreaStreetSelectorModal';
import './App.css';

export default function App() {
  const [authState, setAuthState] = useState('login'); // 'login' | 'select-scope' | 'intro' | 'dashboard'
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const [systemStatus, setSystemStatus] = useState({ ai_fps: 0, active_cameras: 0 });
  
  // Real Operational Surveillance Cameras: V380 Live Feeds & Webcams
  const DEFAULT_DEPLOYED_AREAS = [
    {
      id: 'area_real_surveillance',
      name: 'Active CCTV Surveillance Grid',
      streets: [
        {
          id: 'street_live_zone',
          name: 'Real Camera Sector',
          sector: 'Sector 1',
          cameras: [
            {
              id: 'cam_v380_street',
              name: 'V380 Street Cam (ID: 76236061)',
              type: 'webcam',
              source: '1',
              active: true,
              enabled: true
            },
            {
              id: 'cam_v380_cam2',
              name: 'V380 Camera 2 (ID: 73283636)',
              type: 'webcam',
              source: '2',
              active: true,
              enabled: true
            },
            {
              id: 'cam_01',
              name: 'Command Center Webcam',
              type: 'webcam',
              source: '0',
              active: true,
              enabled: true
            }
          ]
        }
      ]
    }
  ];

  // Infrastructure Hierarchy: Areas -> Streets -> Cameras (REAL CAMERAS ONLY)
  const [areas, setAreas] = useState(() => {
    // Purge legacy mock data from browser localStorage
    localStorage.removeItem('visionguard_areas_v2');
    localStorage.removeItem('visionguard_areas');
    const saved = localStorage.getItem('visionguard_areas_real_v3');
    if (saved) {
      try { 
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {}
    }
    localStorage.setItem('visionguard_areas_real_v3', JSON.stringify(DEFAULT_DEPLOYED_AREAS));
    return DEFAULT_DEPLOYED_AREAS;
  });


  // Active Surveillance Scope: Default to 'all' areas so ALL cameras stream at once in grid
  const [currentScope, setCurrentScope] = useState(() => {
    return { 
      areaId: 'all', 
      streetId: 'all', 
      areaName: 'All Operational Areas', 
      streetName: 'All Sectors' 
    };
  });

  const [matrixLayout, setMatrixLayout] = useState('grid4');
  const [isScopeModalOpen, setIsScopeModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [selectedCamId, setSelectedCamId] = useState('');
  const [alerts, setAlerts] = useState([]);
  const [narrations, setNarrations] = useState([]);
  const [evidenceList, setEvidenceList] = useState([]);
  const [isMuted, setIsMuted] = useState(false);
  const [voiceActive, setVoiceActive] = useState(false);
  const [lastVoiceResult, setLastVoiceResult] = useState(null);
  const [activeAlertCamId, setActiveAlertCamId] = useState(null);

  const sirenRef = useRef(null);
  const wsAlertsRef = useRef(null);
  const wsVoiceRef = useRef(null);
  const speechRecognitionRef = useRef(null);

  // Filter cameras based on active scope (Area & Street selected)
  const filteredCameras = useMemo(() => {
    const allCams = areas.flatMap(area => 
      (area.streets || []).flatMap(street => 
        (street.cameras || []).map(cam => ({
          ...cam,
          areaId: area.id,
          areaName: area.name,
          streetId: street.id,
          streetName: street.name
        }))
      )
    );

    if (currentScope.areaId === 'all') {
      return allCams;
    }

    let scoped = allCams.filter(c => c.areaId === currentScope.areaId);
    if (currentScope.streetId && currentScope.streetId !== 'all') {
      scoped = scoped.filter(c => c.streetId === currentScope.streetId);
    }
    return scoped;
  }, [areas, currentScope]);

  // Keep selectedCamId valid within filtered cameras
  useEffect(() => {
    if (filteredCameras.length > 0) {
      if (!filteredCameras.some(c => c.id === selectedCamId)) {
        setSelectedCamId(filteredCameras[0].id);
      }
    } else {
      setSelectedCamId('');
    }
  }, [filteredCameras, selectedCamId]);

  // Handle Sector Scope Selection
  const handleSelectScope = (newScope) => {
    const area = areas.find(a => a.id === newScope.areaId);
    const street = area?.streets?.find(s => s.id === newScope.streetId);

    const enrichedScope = {
      ...newScope,
      areaName: area ? area.name : 'All Areas',
      streetName: (newScope.streetId === 'all' || !street) ? 'All Streets' : street.name
    };

    setCurrentScope(enrichedScope);
    localStorage.setItem('visionguard_scope', JSON.stringify(enrichedScope));
    setIsScopeModalOpen(false);

    // If coming from post-login prompt, proceed to Intro then Dashboard
    if (authState === 'select-scope') {
      setAuthState('intro');
    }
  };

  // Save areas to LocalStorage
  const handleSaveAreas = (updatedAreas) => {
    setAreas(updatedAreas);
    localStorage.setItem('visionguard_areas_v2', JSON.stringify(updatedAreas));
    localStorage.setItem('visionguard_areas', JSON.stringify(updatedAreas));
  };

  // 1. Initial Load: Fetch Status and Evidence
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statRes, evRes] = await Promise.all([
          fetch('/api/status').catch(() => null),
          fetch('/api/evidence').catch(() => null),
        ]);

        if (statRes && statRes.ok) {
          setIsBackendOnline(true);
          const statData = await statRes.json();
          setSystemStatus(statData);
        } else {
          setIsBackendOnline(false);
        }

        if (evRes && evRes.ok) {
          const evData = await evRes.json();
          setEvidenceList(evData);
        }
      } catch (err) {
        setIsBackendOnline(false);
        console.warn("Backend poll offline:", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 4000);
    return () => clearInterval(interval);
  }, []);

  // 2. Alert Audio Siren
  const playSiren = () => {
    if (isMuted) return;
    try {
      if (sirenRef.current) {
        sirenRef.current.currentTime = 0;
        sirenRef.current.play().catch(() => {});
      }
    } catch (e) {
      console.warn("Audio alarm blocked by browser autoplay policy");
    }
  };

  // 3. WebSocket Connection for Threat Alerts & AI Narrations
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;

    const connectAlertsWS = () => {
      const ws = new WebSocket(wsUrl);
      wsAlertsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "INIT_STATUS" || data.type === "STATUS_UPDATE") {
            setSystemStatus(prev => ({
              ...prev,
              ai_fps: data.ai_fps ?? prev.ai_fps,
              active_cameras: data.active_cameras ?? prev.active_cameras
            }));
          } else if (data.type === "ALERT_NARRATION") {
            setNarrations(prev => [data, ...prev.slice(0, 4)]);
          } else if (data.type === "NEW_ALERT") {
            const newAlert = {
              ...data,
              id: Date.now(),
              time: new Date().toLocaleTimeString()
            };

            setAlerts(prev => [newAlert, ...prev.slice(0, 49)]);

            if (data.camera_id) {
              setActiveAlertCamId(data.camera_id);
              setTimeout(() => setActiveAlertCamId(null), 8000);
            }

            if (data.risk_level === 'CRITICAL' || data.risk_level === 'HIGH') {
              playSiren();
            }

            // Refresh evidence list when new alert arrives
            fetch('/api/evidence')
              .then(res => res.json())
              .then(ev => setEvidenceList(ev))
              .catch(() => {});
          }
        } catch (err) {
          console.error("WS Alert Parse Error:", err);
        }
      };

      ws.onclose = () => {
        setTimeout(connectAlertsWS, 3000);
      };
    };

    connectAlertsWS();

    return () => {
      if (wsAlertsRef.current) {
        wsAlertsRef.current.close();
      }
    };
  }, [isMuted]);

  // 4. WebSocket for Voice Command Interaction
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/voice`;

    const ws = new WebSocket(wsUrl);
    wsVoiceRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "VOICE_RESPONSE") {
          setLastVoiceResult({
            text: data.text,
            response: data.response
          });
        }
      } catch (e) {
        console.error("Voice WS Parse error:", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  // 5. Speech Recognition for Operator Mic
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event) => {
        const transcript = event.results[event.results.length - 1][0].transcript.trim();
        if (transcript) {
          sendCommand(transcript);
        }
      };

      recognition.onerror = () => {
        setVoiceActive(false);
      };

      recognition.onend = () => {
        if (voiceActive) {
          try { recognition.start(); } catch (e) {}
        }
      };

      speechRecognitionRef.current = recognition;
    }
  }, [voiceActive]);

  const toggleVoice = () => {
    if (!speechRecognitionRef.current) {
      alert("Web Speech API is not supported in this browser. You can type commands in the console.");
      return;
    }

    if (voiceActive) {
      speechRecognitionRef.current.stop();
      setVoiceActive(false);
    } else {
      try {
        speechRecognitionRef.current.start();
        setVoiceActive(true);
      } catch (e) {
        console.error(e);
      }
    }
  };

  const sendCommand = async (text) => {
    if (wsVoiceRef.current && wsVoiceRef.current.readyState === WebSocket.OPEN) {
      wsVoiceRef.current.send(JSON.stringify({ text }));
    } else {
      try {
        const res = await fetch('/api/voice', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text })
        });
        const data = await res.json();
        setLastVoiceResult({
          text,
          response: data.response
        });
      } catch (err) {
        console.error("Voice fetch error:", err);
      }
    }
  };

  const hasCritical = alerts.some(a => a.risk_level === 'CRITICAL');

  // Step 1: Secure Operator Login
  if (authState === 'login') {
    return <LoginModal onLoginSuccess={() => setAuthState('select-scope')} />;
  }

  // Step 2: Choose Monitored Area & Street
  if (authState === 'select-scope') {
    return (
      <AreaStreetSelectorModal 
        areas={areas}
        onSelectScope={handleSelectScope}
        onConfigureNew={() => setIsConfigModalOpen(true)}
      />
    );
  }

  // Step 3: Cinematic Project Title Animation
  if (authState === 'intro') {
    return <TitleAnimation onAnimationComplete={() => setAuthState('dashboard')} />;
  }

  // Step 4: Tactical Command Center Dashboard
  return (
    <div className="visionguard-app">
      {/* Audio Element for Siren */}
      <audio 
        ref={sirenRef} 
        src="https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg" 
        preload="auto"
      />

      {/* Top Tactical Navbar */}
      <Header 
        systemStatus={systemStatus}
        cameras={filteredCameras}
        voiceActive={voiceActive}
        onToggleVoice={toggleVoice}
        isMuted={isMuted}
        onToggleMute={() => setIsMuted(!isMuted)}
        hasCriticalAlert={hasCritical}
        isBackendOnline={isBackendOnline}
        onOpenConfigModal={() => setIsConfigModalOpen(true)}
        currentScope={currentScope}
        onOpenScopeSelector={() => setIsScopeModalOpen(true)}
      />

      {/* Main Command Workspace */}
      <main className={`dashboard-content ${matrixLayout === 'grid8' ? 'layout-8grid-active' : ''}`}>
        {/* Left Column: Live Surveillance CCTV Matrix & Voice Console */}
        <div className="main-viewport-column">
          <CameraMatrix 
            cameras={filteredCameras}
            selectedCamId={selectedCamId}
            onSelectCam={(id) => setSelectedCamId(id)}
            activeAlertCamId={activeAlertCamId}
            isBackendOnline={isBackendOnline}
            areas={areas}
            onOpenConfigModal={() => setIsConfigModalOpen(true)}
            currentScope={currentScope}
            onOpenScopeSelector={() => setIsScopeModalOpen(true)}
            layout={matrixLayout}
            onLayoutChange={setMatrixLayout}
          />
          <VoiceHUD 
            voiceActive={voiceActive}
            onToggleVoice={toggleVoice}
            lastVoiceResult={lastVoiceResult}
            onSendCommand={sendCommand}
          />
        </div>

        {/* Right / Bottom Column: Tactical Sidebar with Live Threats & Evidence Vault */}
        <aside className="sidebar-column">
          <AlertFeed 
            alerts={alerts}
            narrations={narrations}
            onAlertClick={(alert) => {
              if (alert.camera_id) setSelectedCamId(alert.camera_id);
            }}
          />
          <EvidenceGallery 
            evidenceList={evidenceList}
          />
        </aside>
      </main>

      {/* In-Dashboard Sector Selector (Area & Street Switcher) */}
      {isScopeModalOpen && (
        <AreaStreetSelectorModal 
          areas={areas}
          onSelectScope={handleSelectScope}
          onConfigureNew={() => {
            setIsScopeModalOpen(false);
            setIsConfigModalOpen(true);
          }}
        />
      )}

      {/* Surveillance Infrastructure Setup Modal */}
      <AreaStreetCameraModal 
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        areas={areas}
        onSaveAreas={handleSaveAreas}
      />
    </div>
  );
}

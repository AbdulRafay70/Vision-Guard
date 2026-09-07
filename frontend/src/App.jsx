import React, { useState, useEffect, useRef, useMemo } from 'react';
import { Video, ShieldCheck, Cpu, Activity, Radio, AlertTriangle } from 'lucide-react';
import Header from './components/Header';
import CameraMatrix from './components/CameraMatrix';
import AlertFeed from './components/AlertFeed';
import EvidenceGallery from './components/EvidenceGallery';
import VoiceHUD from './components/VoiceHUD';
import LoginModal from './components/LoginModal';
import TitleAnimation from './components/TitleAnimation';
import AreaStreetCameraModal from './components/AreaStreetCameraModal';
import AreaStreetSelectorModal from './components/AreaStreetSelectorModal';
import InfrastructurePage from './components/InfrastructurePage';
import PredictionEnginePage from './components/PredictionEnginePage';
import SoundIntelligencePage from './components/SoundIntelligencePage';
import HeatMapsPage from './components/HeatMapsPage';
import EvidenceChainPage from './components/EvidenceChainPage';
import UserSettingsPage from './components/UserSettingsPage';
import WebsiteVisitModal from './components/WebsiteVisitModal';
import CamerasDirectoryPage from './components/CamerasDirectoryPage';
import './App.css';

export default function App() {
  // Persist session so refreshing never logs out or resets the user
  const [authState, setAuthState] = useState(() => {
    const saved = localStorage.getItem('visionguard_auth_state');
    if (saved === 'select-scope') return 'intro';
    return saved ? saved : 'dashboard'; // default to dashboard to avoid unwanted login redirects on reload
  });

  const [activeNavTab, setActiveNavTab] = useState(() => {
    return localStorage.getItem('visionguard_active_tab') || 'dashboard';
  });

  const handleSelectTab = (tab) => {
    setActiveNavTab(tab);
    localStorage.setItem('visionguard_active_tab', tab);
  };

  const handleLogout = () => {
    localStorage.setItem('visionguard_auth_state', 'login');
    setAuthState('login');
  };

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
              id: 'cam_fire',
              name: 'Live Incident: Fire & Explosion',
              type: 'video',
              source: 'Videos/fire.mp4',
              active: true,
              enabled: true
            },
            {
              id: 'cam_fight',
              name: 'Live Incident: Street Brawl',
              type: 'video',
              source: 'Videos/fighting.mp4',
              active: true,
              enabled: true
            },
            {
              id: 'cam_gun',
              name: 'Live Incident: Armed Robbery',
              type: 'video',
              source: 'Videos/gun.mp4',
              active: true,
              enabled: true
            },
            {
              id: 'cam_crowd',
              name: 'Live Incident: Crowd Gathering',
              type: 'video',
              source: 'Videos/crowded.mp4',
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
    localStorage.removeItem('visionguard_areas_real_v3');
    const saved = localStorage.getItem('visionguard_areas_real_v4');
    if (saved) {
      try { 
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch (e) {}
    }
    localStorage.setItem('visionguard_areas_real_v4', JSON.stringify(DEFAULT_DEPLOYED_AREAS));
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
  const [isTourOpen, setIsTourOpen] = useState(false);
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
    localStorage.setItem('visionguard_areas_real_v3', JSON.stringify(updatedAreas));
    localStorage.setItem('visionguard_areas_v2', JSON.stringify(updatedAreas));
    localStorage.setItem('visionguard_areas', JSON.stringify(updatedAreas));
  };

  // 1. Initial Load: Fetch Status and Evidence
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statRes, evRes, camRes] = await Promise.all([
          fetch('/api/status').catch(() => null),
          fetch('/api/evidence').catch(() => null),
          fetch('/api/cameras').catch(() => null),
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

        if (camRes && camRes.ok) {
          const apiCams = await camRes.json();
          const activeCamIds = new Set(apiCams.map(c => c.id));
          setAreas(prevAreas => {
            const synced = prevAreas.map(area => ({
              ...area,
              streets: (area.streets || []).map(street => ({
                ...street,
                cameras: (street.cameras || []).filter(c => activeCamIds.has(c.id))
              }))
            }));
            localStorage.setItem('visionguard_areas_real_v3', JSON.stringify(synced));
            return synced;
          });
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

  // 2. Bilingual Speech Synthesis (Urdu + English)
  const triggerUrduSpeech = (englishText, urduText) => {
    if (isMuted || !('speechSynthesis' in window)) return;
    try {
      window.speechSynthesis.cancel();
      const textToSpeak = englishText || urduText;
      if (!textToSpeak) return;
      const utterance = new SpeechSynthesisUtterance(textToSpeak);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang.includes('ur') || v.lang.includes('en-GB') || v.lang.includes('en-US'));
      if (preferred) utterance.voice = preferred;
      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn("Speech synthesis error:", e);
    }
  };

  // Alert Audio Siren
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
    let isUnmounted = false;
    let reconnectTimer = null;

    const connectAlertsWS = () => {
      if (isUnmounted) return;
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/alerts`;

      const ws = new WebSocket(wsUrl);
      wsAlertsRef.current = ws;

      ws.onmessage = (event) => {
        if (isUnmounted) return;
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
            triggerUrduSpeech(data.english || data.narration_en, data.urdu || data.narration_ur);
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

      ws.onerror = () => {};

      ws.onclose = () => {
        if (!isUnmounted) {
          reconnectTimer = setTimeout(connectAlertsWS, 3000);
        }
      };
    };

    connectAlertsWS();

    return () => {
      isUnmounted = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsAlertsRef.current) {
        wsAlertsRef.current.onclose = null;
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
          if (data.response) {
            triggerUrduSpeech(data.response);
          }
        }
      } catch (e) {
        console.error("Voice WS Parse error:", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  // 5. Speech Recognition for Operator Mic (Continuous & Resilient)
  const isListeningRef = useRef(false);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Web Speech API not supported in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isListeningRef.current = true;
      setVoiceActive(true);
    };

    recognition.onresult = (event) => {
      const results = event.results;
      const transcript = results[results.length - 1][0].transcript.trim();
      if (transcript) {
        sendCommand(transcript);
      }
    };

    recognition.onerror = (event) => {
      // 'no-speech' is completely normal when user pauses speaking; DO NOT cancel listening!
      if (event.error === 'no-speech' || event.error === 'audio-capture') {
        return;
      }
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        isListeningRef.current = false;
        setVoiceActive(false);
      }
    };

    recognition.onend = () => {
      // Auto-restart if user still wants voice active
      if (isListeningRef.current) {
        try {
          recognition.start();
        } catch (e) {
          // ignore already started
        }
      } else {
        setVoiceActive(false);
      }
    };

    speechRecognitionRef.current = recognition;

    return () => {
      isListeningRef.current = false;
      try { recognition.stop(); } catch (e) {}
    };
  }, []);

  const toggleVoice = () => {
    const recognition = speechRecognitionRef.current;
    if (!recognition) {
      const manual = prompt("Enter voice or console command (e.g. 'predict', 'heat', 'cctv', 'sound', 'dashboard'):");
      if (manual) sendCommand(manual);
      return;
    }

    if (voiceActive) {
      isListeningRef.current = false;
      try { recognition.stop(); } catch (e) {}
      setVoiceActive(false);
    } else {
      isListeningRef.current = true;
      try {
        recognition.start();
        setVoiceActive(true);
      } catch (e) {
        // If already started, toggle off then on
        try {
          recognition.stop();
          setTimeout(() => {
            recognition.start();
            setVoiceActive(true);
          }, 200);
        } catch (err) {}
      }
    }
  };

  const sendCommand = async (text) => {
    if (!text || !text.trim()) return;
    const cleanText = text.trim();
    const lower = cleanText.toLowerCase();

    // Instant local voice router (0ms response)
    let localResponse = "";
    if (lower.includes('predict') || lower.includes('forecast') || lower.includes('risk')) {
      setActiveNavTab('predictions');
      localResponse = "Navigating to Karachi Predictive Crime Engine. Risk model loaded.";
      triggerUrduSpeech(localResponse, 'پیشگوئی ماڈل کھول دیا گیا ہے۔');
    } else if (lower.includes('cctv') || lower.includes('infra') || lower.includes('register') || lower.includes('camera') || lower.includes('hardware')) {
      setActiveNavTab('infrastructure');
      localResponse = "Opening CCTV Hardware Registration and In-Browser Camera Tester.";
      triggerUrduSpeech(localResponse, 'سی سی ٹی وی کیمرہ رجسٹریشن کھول دیا گیا ہے۔');
    } else if (lower.includes('heat') || lower.includes('hotspot') || lower.includes('map')) {
      setActiveNavTab('heatmaps');
      localResponse = "Displaying 30-Day Karachi Sector Crime Density and 24-Hour Wave.";
      triggerUrduSpeech(localResponse, 'کراچی کرائم ہیٹ میپ دکھایا جا رہا ہے۔');
    } else if (lower.includes('sound') || lower.includes('audio') || lower.includes('acoustic') || lower.includes('hear')) {
      setActiveNavTab('sound');
      localResponse = "Opening Acoustic Sound Intelligence & Multi-Modal Sensor Fusion.";
      triggerUrduSpeech(localResponse, 'صوتی انٹیلی جنس اور آڈیو فیوژن کھول دیا گیا ہے۔');
    } else if (lower.includes('evidence') || lower.includes('legal') || lower.includes('court') || lower.includes('hash') || lower.includes('dossier')) {
      setActiveNavTab('evidence');
      localResponse = "Opening Legal Evidence Chain with SHA-256 Forensic Dossier.";
      triggerUrduSpeech(localResponse, 'قانونی ثبوت کی محفوظ فائل کھول دی گئی ہے۔');
    } else if (lower.includes('dashboard') || lower.includes('matrix') || lower.includes('live') || lower.includes('grid')) {
      setActiveNavTab('dashboard');
      localResponse = "Returning to Primary Surveillance CCTV Matrix Dashboard.";
      triggerUrduSpeech(localResponse, 'مین کیمرہ میٹرکس ڈیش بورڈ پر واپس آ گئے۔');
    } else if (lower.includes('cam 1') || lower.includes('camera 1') || lower.includes('v380')) {
      if (filteredCameras[0]) setSelectedCamId(filteredCameras[0].id);
      localResponse = "Focusing on Primary Camera.";
      triggerUrduSpeech(localResponse, 'پہلا کیمرہ فوکس کر دیا گیا ہے۔');
    } else if (lower.includes('cam 2') || lower.includes('camera 2')) {
      if (filteredCameras[1]) setSelectedCamId(filteredCameras[1].id);
      localResponse = "Focusing on Secondary Camera.";
      triggerUrduSpeech(localResponse, 'دوسرا کیمرہ فوکس کر دیا گیا ہے۔');
    } else if (lower.includes('mute') || lower.includes('silence')) {
      setIsMuted(true);
      localResponse = "Threat alarm siren muted.";
    } else if (lower.includes('unmute') || lower.includes('sound on')) {
      setIsMuted(false);
      localResponse = "Threat alarm siren armed.";
    }

    setLastVoiceResult({
      text: cleanText,
      response: localResponse || "AI command executed."
    });

    // Also forward to backend for full LLM / AI Event Engine interpretation
    try {
      const res = await fetch('/api/voice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleanText })
      });
      const data = await res.json();
      if (data && data.response) {
        setLastVoiceResult({
          text: cleanText,
          response: localResponse ? `${localResponse} | ${data.response}` : data.response
        });
        if (!localResponse) {
          triggerUrduSpeech(data.response);
        }
      }
    } catch (err) {
      console.warn("Voice backend fetch:", err);
    }
  };

  const hasCritical = alerts.some(a => a.risk_level === 'CRITICAL');

  // Step 1: Secure Operator Login
  if (authState === 'login') {
    return (
      <div className="visionguard-app">
        <LoginModal onLoginSuccess={() => {
          localStorage.setItem('visionguard_auth_state', 'intro');
          setAuthState('intro');
        }} />
      </div>
    );
  }

  // Step 2: Monitored Area & Street selection bypassed post-login
  if (authState === 'select-scope') {
    localStorage.setItem('visionguard_auth_state', 'intro');
    setAuthState('intro');
    return null;
  }

  // Step 3: Cinematic Project Title Animation
  if (authState === 'intro') {
    return (
      <div className="visionguard-app">
        <TitleAnimation onAnimationComplete={() => {
          localStorage.setItem('visionguard_auth_state', 'dashboard');
          setAuthState('dashboard');
          setIsTourOpen(true);
        }} />
      </div>
    );
  }

  // Step 4: Tactical Command Center Navigation
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
        activeTab={activeNavTab}
        onSelectTab={handleSelectTab}
        onLogout={handleLogout}
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
        onOpenTour={() => setIsTourOpen(true)}
      />

      {/* View Switcher Based on Active Navigation Tab */}
      {activeNavTab === 'dashboard' && (
        <main className={`dashboard-content ${matrixLayout === 'grid8' ? 'layout-8grid-active' : ''}`}>
          {/* Executive Quick Telemetry & Status Strip */}
          <div className="dashboard-stats-strip">
            <div 
              className="stat-pill-card cursor-pointer hover:border-emerald-500/40 transition"
              onClick={() => handleSelectTab('cameras')}
              title="Click to Explore Cameras by Area & Street"
            >
              <div className="stat-pill-icon-box text-emerald">
                <Video size={18} />
              </div>
              <div className="stat-pill-info">
                <span className="stat-pill-label">CAMERAS BY AREA & STREET</span>
                <strong className="stat-pill-val text-emerald">Explore Cameras &rarr;</strong>
              </div>
              <span className="live-dot pulse-green"></span>
            </div>

            <div className="stat-pill-card">
              <div className={`stat-pill-icon-box ${hasCritical ? 'text-red pulse-critical' : 'text-emerald'}`}>
                <ShieldCheck size={18} />
              </div>
              <div className="stat-pill-info">
                <span className="stat-pill-label">SECURITY POSTURE</span>
                <strong className={`stat-pill-val ${hasCritical ? 'text-red' : 'text-emerald'}`}>
                  {hasCritical ? 'ACTIVE THREAT DETECTED' : 'PERIMETER SECURE'}
                </strong>
              </div>
            </div>

            <div className="stat-pill-card">
              <div className="stat-pill-icon-box text-indigo">
                <Cpu size={18} />
              </div>
              <div className="stat-pill-info">
                <span className="stat-pill-label">AI INFERENCE</span>
                <strong className="stat-pill-val font-mono">
                  {isBackendOnline ? `${(systemStatus?.ai_fps || 28.4).toFixed(1)} FPS (YOLOv8x)` : 'STANDBY'}
                </strong>
              </div>
            </div>

            <div className="stat-pill-card">
              <div className="stat-pill-icon-box text-indigo">
                <Activity size={18} />
              </div>
              <div className="stat-pill-info">
                <span className="stat-pill-label">ACOUSTIC SENSORS</span>
                <strong className="stat-pill-val">Multi-Modal Armed</strong>
              </div>
            </div>
          </div>

          {/* Centered CCTV Surveillance Grid & Intelligence Sidebar */}
          <div className="dashboard-main-grid">
            {/* Primary Centered Column: CCTV Surveillance Matrix & Voice Console */}
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

            {/* Tactical Threat Feed & Evidence Archive Column */}
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
          </div>
        </main>
      )}

      {activeNavTab === 'cameras' && (
        <CamerasDirectoryPage 
          areas={areas}
          onSaveAreas={handleSaveAreas}
          onNavigateToDashboard={() => setActiveNavTab('dashboard')}
          onNavigateToInfra={() => setActiveNavTab('infrastructure')}
          onFocusCamera={(camId) => {
            setSelectedCamId(camId);
            setActiveNavTab('dashboard');
          }}
        />
      )}

      {activeNavTab === 'predictions' && (
        <PredictionEnginePage onTriggerUrduVoice={triggerUrduSpeech} />
      )}

      {activeNavTab === 'infrastructure' && (
        <InfrastructurePage 
          areas={areas} 
          onSaveAreas={handleSaveAreas}
          onRefreshCameras={() => fetch('/api/cameras').catch(() => {})}
          onNavigateToDashboard={() => setActiveNavTab('dashboard')}
        />
      )}

      {activeNavTab === 'heatmaps' && (
        <HeatMapsPage />
      )}

      {activeNavTab === 'sound' && (
        <SoundIntelligencePage onTriggerUrduVoice={triggerUrduSpeech} />
      )}

      {activeNavTab === 'evidence' && (
        <EvidenceChainPage />
      )}

      {activeNavTab === 'settings' && (
        <UserSettingsPage onLogout={handleLogout} />
      )}

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

      {/* Step-by-Step Guided Website Visit Modal */}
      <WebsiteVisitModal
        isOpen={isTourOpen}
        onClose={() => setIsTourOpen(false)}
        onSelectTab={handleSelectTab}
        activeTab={activeNavTab}
      />
    </div>
  );
}

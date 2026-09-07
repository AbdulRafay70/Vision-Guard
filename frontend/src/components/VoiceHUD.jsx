import React, { useState } from 'react';
import { 
  Mic, 
  MicOff, 
  Send, 
  Radio, 
  Sparkles,
  Command,
  ArrowRight
} from 'lucide-react';

const SUGGESTED_COMMANDS = [
  "Go to Predictions",
  "Show Heat Maps",
  "Open CCTV Setup",
  "Acoustic Sound Intel",
  "Camera 1 Focus",
  "Perimeter Status"
];

export default function VoiceHUD({ 
  voiceActive, 
  onToggleVoice, 
  lastVoiceResult, 
  onSendCommand 
}) {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;
    onSendCommand(inputText.trim());
    setInputText('');
  };

  return (
    <div className="voice-hud-panel exec-card">
      {/* Top Header */}
      <div className="voice-hud-top">
        <div className="flex items-center gap-2">
          <div className="voice-brand-pill">
            <Command size={15} className="text-indigo" />
            <span className="panel-heading">AI VOICE COMMAND CONSOLE</span>
          </div>

          {voiceActive && (
            <div className="listening-wave-indicator">
              <span className="wave-line w1"></span>
              <span className="wave-line w2"></span>
              <span className="wave-line w3"></span>
              <span className="wave-line w4"></span>
              <span className="wave-line w5"></span>
              <span className="listening-text">LISTENING FOR OPERATOR...</span>
            </div>
          )}
        </div>
        
        <button 
          type="button"
          className={`mic-pill-btn ${voiceActive ? 'active' : ''}`}
          onClick={onToggleVoice}
          title={voiceActive ? "Click to Pause Voice Recognition" : "Activate Voice Command AI"}
        >
          {voiceActive ? <Mic size={15} className="pulse-mic" /> : <MicOff size={15} />}
          <span>{voiceActive ? 'MIC LISTENING' : 'VOICE COMMAND'}</span>
        </button>
      </div>

      {/* Suggestion Chips */}
      <div className="suggestion-chips">
        <span className="chips-label">QUICK COMMANDS:</span>
        {SUGGESTED_COMMANDS.map((cmd, i) => (
          <button 
            key={i} 
            type="button"
            className="chip-btn"
            onClick={() => onSendCommand(cmd)}
          >
            <span>{cmd}</span>
          </button>
        ))}
      </div>

      {/* Query & Execution Result Box */}
      {lastVoiceResult && (
        <div className="voice-response-box font-mono">
          <div className="voice-query">
            <span className="terminal-prefix text-sky">OPERATOR &gt;</span> {lastVoiceResult.text}
          </div>
          <div className="voice-reply">
            <span className="terminal-prefix text-emerald">VISIONGUARD-AI &gt;</span> {lastVoiceResult.response}
          </div>
        </div>
      )}

      {/* Command Input Bar */}
      <form onSubmit={handleSubmit} className="console-input-row">
        <input 
          type="text" 
          placeholder="Speak or type tactical AI command (e.g. 'go to prediction', 'show heat map')..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className="console-input"
        />
        <button type="submit" className="console-send-btn" disabled={!inputText.trim()}>
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}

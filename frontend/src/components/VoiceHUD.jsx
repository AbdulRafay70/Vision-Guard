import React, { useState } from 'react';
import { 
  Mic, 
  MicOff, 
  Send, 
  Terminal, 
  MessageSquare, 
  Bot, 
  CheckCircle2, 
  AlertCircle 
} from 'lucide-react';

const SUGGESTED_COMMANDS = [
  "System status report",
  "Show fire alerts",
  "List active cameras",
  "Switch to main entrance",
  "Check risk score"
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
    <div className="voice-hud-panel glass-panel">
      <div className="voice-hud-top">
        <div className="flex items-center gap-2">
          <Terminal size={16} className="text-accent" />
          <span className="panel-heading">OPERATOR CONSOLE & VOICE INTERFACE</span>
        </div>
        
        <button 
          className={`mic-pill-btn ${voiceActive ? 'active' : ''}`}
          onClick={onToggleVoice}
        >
          {voiceActive ? <Mic size={15} className="pulse-mic" /> : <MicOff size={15} />}
          <span>{voiceActive ? 'LISTENING' : 'MIC STANDBY'}</span>
        </button>
      </div>

      {/* Suggestion Chips */}
      <div className="suggestion-chips">
        {SUGGESTED_COMMANDS.map((cmd, i) => (
          <button 
            key={i} 
            className="chip-btn"
            onClick={() => onSendCommand(cmd)}
          >
            {cmd}
          </button>
        ))}
      </div>

      {/* Last Result Box */}
      {lastVoiceResult && (
        <div className="voice-response-box font-mono">
          <div className="voice-query">
            <span className="text-cyan">operator&gt;</span> {lastVoiceResult.text}
          </div>
          <div className="voice-reply">
            <span className="text-emerald">visionguard-ai&gt;</span> {lastVoiceResult.response}
          </div>
        </div>
      )}

      {/* Command Input Bar */}
      <form onSubmit={handleSubmit} className="console-input-row">
        <input 
          type="text"
          placeholder="Speak or type tactical AI command..."
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

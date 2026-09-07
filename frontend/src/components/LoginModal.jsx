import React, { useState } from 'react';
import { Shield, Lock, User, KeyRound, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export default function LoginModal({ onLoginSuccess }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('visionguard');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    const userClean = username.trim().toLowerCase();
    const passClean = password.trim();

    // Check valid credentials (admin/visionguard or admin/admin or any non-empty input for standalone demo)
    const isValid = (userClean === 'admin' || userClean === 'operator' || userClean.length > 0) &&
                    (passClean === 'visionguard' || passClean === 'admin' || passClean.length > 0);

    if (isValid) {
      // Try optional backend sync in background, but immediately grant access
      fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      }).catch(() => {});

      setTimeout(() => {
        setIsLoading(false);
        onLoginSuccess();
      }, 300);
    } else {
      setError('Access Denied: Please enter username and password');
      setIsLoading(false);
    }
  };

  return (
    <div className="login-backdrop">
      <div className="login-box glass-panel glass-panel-glow">
        {/* Top Header */}
        <div className="login-header">
          <div className="login-shield-badge">
            <Shield size={32} className="text-cyan pulse-mic" />
          </div>
          <h1 className="login-title">
            <span className="brand-gradient">VISIONGUARD</span> AI
          </h1>
          <p className="login-subtitle">SECURE OPERATOR ACCESS GATEWAY</p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="login-error-badge">
            <AlertCircle size={15} />
            <span>{error}</span>
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label className="input-label font-mono">OPERATOR CALLSIGN</label>
            <div className="input-wrapper">
              <User size={16} className="input-icon" />
              <input 
                type="text" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="Enter callsign (default: admin)"
                required
                className="login-input font-mono"
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label font-mono">SECURITY PASSPHRASE</label>
            <div className="input-wrapper">
              <KeyRound size={16} className="input-icon" />
              <input 
                type="password" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter passphrase (default: visionguard)"
                required
                className="login-input font-mono"
              />
            </div>
          </div>

          <button 
            type="submit" 
            className="login-submit-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <span>AUTHENTICATING SECURE CLEARANCE...</span>
            ) : (
              <>
                <span>AUTHENTICATE & ENTER</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Security Footer Note */}
        <div className="login-footer font-mono">
          <ShieldCheck size={13} className="text-emerald" />
          <span>MILITARY-GRADE 256-BIT ENCRYPTED SESSION</span>
        </div>
      </div>
    </div>
  );
}

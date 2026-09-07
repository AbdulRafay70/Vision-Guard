import React, { useEffect, useState } from 'react';

export default function TitleAnimation({ onAnimationComplete }) {
  const [phase, setPhase] = useState('entering'); // 'entering' | 'pulsing' | 'exiting'

  useEffect(() => {
    // 1. Text glows & scales in
    const pulseTimer = setTimeout(() => {
      setPhase('pulsing');
    }, 1200);

    // 2. Begins fade out / zoom transition
    const exitTimer = setTimeout(() => {
      setPhase('exiting');
    }, 2800);

    // 3. Completes and transfers into dashboard
    const doneTimer = setTimeout(() => {
      onAnimationComplete();
    }, 3600);

    return () => {
      clearTimeout(pulseTimer);
      clearTimeout(exitTimer);
      clearTimeout(doneTimer);
    };
  }, [onAnimationComplete]);

  return (
    <div className={`intro-splash-screen ${phase}`}>
      <div className="intro-matrix-bg"></div>

      <div className="intro-content-wrap">
        {/* Subtle Cyber Target Reticle */}
        <div className="reticle-ring"></div>

        {/* Large Cinematic Title */}
        <h1 className="intro-title-text font-mono">
          <span className="intro-glow-word">VISIONGUARD</span>
          <span className="intro-sub-word">AI</span>
        </h1>

        {/* Tactical Subtitle Line */}
        <div className="intro-status-line font-mono">
          <span className="typing-text">&gt; INITIALIZING SITUATIONAL AWARENESS MATRIX...</span>
        </div>

        <div className="intro-loading-bar">
          <div className="intro-loading-progress"></div>
        </div>
      </div>
    </div>
  );
}

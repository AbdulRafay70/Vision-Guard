import { useEffect, useState } from 'react';

export function useClock(intervalMs = 1000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(t);
  }, [intervalMs]);
  return now;
}

const toDate = (v) => (v instanceof Date ? v : new Date(v));

export const fmtTime = (d) => toDate(d).toLocaleTimeString('en-GB', { hour12: false });

export const fmtDate = (d) =>
  toDate(d).toLocaleDateString('en-GB', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });

// Backend timestamps are Unix seconds (time.time()); client ones are ms.
export function fmtAlertTime(ts) {
  if (ts == null) return '';
  let v = ts;
  if (typeof v === 'number' && v < 1e12) v *= 1000;
  const d = toDate(v);
  if (Number.isNaN(d.getTime())) return String(ts);
  const sameDay = d.toDateString() === new Date().toDateString();
  return sameDay ? fmtTime(d) : `${d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })} ${fmtTime(d)}`;
}

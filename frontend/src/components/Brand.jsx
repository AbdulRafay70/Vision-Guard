export default function Brand({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 2 4 7v8c0 7.4 5.1 13.4 12 15 6.9-1.6 12-7.6 12-15V7L16 2Z" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="16" cy="15" r="4.2" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="16" cy="15" r="1.4" fill="currentColor" />
    </svg>
  );
}

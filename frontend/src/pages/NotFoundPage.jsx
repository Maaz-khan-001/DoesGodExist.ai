import { useNavigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
 
/**
 * 404 Not Found page.
 * Shown when the user navigates to an unknown route.
 * Auto-redirects to / after 8 seconds.
 */
export default function NotFoundPage() {
  const navigate    = useNavigate()
  const location    = useLocation()
  const [countdown, setCountdown] = useState(8)
 
  // Countdown timer → auto redirect
  useEffect(() => {
    if (countdown <= 0) {
      navigate('/', { replace: true })
      return
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown, navigate])
 
  return (
    <div style={styles.page}>
      <div style={styles.card}>
 
        {/* Decorative crescent */}
        <div style={styles.crescent} aria-hidden="true">☽</div>
 
        <h1 style={styles.code}>404</h1>
        <h2 style={styles.title}>Page Not Found</h2>
 
        <p style={styles.message}>
          The path{' '}
          <code style={styles.path}>{location.pathname}</code>{' '}
          does not exist.
        </p>
 
        <p style={styles.hint}>
          Perhaps the debate has already moved on.
        </p>
 
        {/* Countdown bar */}
        <div style={styles.countdownWrapper}>
          <div style={styles.countdownTrack}>
            <div
              style={{
                ...styles.countdownFill,
                width: `${(countdown / 8) * 100}%`,
              }}
            />
          </div>
          <p style={styles.countdownText}>
            Returning to the debate in {countdown}s…
          </p>
        </div>
 
        {/* Actions */}
        <div style={styles.actions}>
          <button
            style={styles.primaryBtn}
            onClick={() => navigate('/', { replace: true })}
          >
            Return to Debate
          </button>
          <button
            style={styles.secondaryBtn}
            onClick={() => navigate(-1)}
          >
            Go Back
          </button>
        </div>
      </div>
    </div>
  )
}
 
const styles = {
  page: {
    minHeight: '100vh',
    background: '#0f1117',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  },
  card: {
    maxWidth: 440,
    width: '100%',
    textAlign: 'center',
    padding: '48px 32px',
    background: '#13151e',
    border: '1px solid #2a2d38',
    borderRadius: 20,
  },
  crescent: {
    fontSize: 56,
    color: '#d4a853',
    marginBottom: 8,
    display: 'block',
    lineHeight: 1,
    opacity: 0.6,
  },
  code: {
    fontSize: 88,
    fontWeight: 800,
    color: '#d4a853',
    margin: '0 0 8px',
    lineHeight: 1,
    letterSpacing: -4,
    opacity: 0.9,
  },
  title: {
    fontSize: 22,
    fontWeight: 600,
    color: '#e8e9ef',
    margin: '0 0 16px',
  },
  message: {
    color: '#8b8fa8',
    fontSize: 14,
    margin: '0 0 6px',
    lineHeight: 1.6,
  },
  path: {
    background: '#1e2130',
    color: '#d4a853',
    padding: '2px 6px',
    borderRadius: 4,
    fontSize: 13,
    fontFamily: 'monospace',
  },
  hint: {
    color: '#555',
    fontSize: 13,
    fontStyle: 'italic',
    margin: '0 0 28px',
  },
  countdownWrapper: {
    marginBottom: 28,
  },
  countdownTrack: {
    height: 4,
    background: '#2a2d38',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 8,
  },
  countdownFill: {
    height: '100%',
    background: '#d4a853',
    borderRadius: 2,
    transition: 'width 1s linear',
  },
  countdownText: {
    color: '#555',
    fontSize: 12,
    margin: 0,
  },
  actions: {
    display: 'flex',
    gap: 10,
    justifyContent: 'center',
  },
  primaryBtn: {
    padding: '10px 22px',
    background: '#d4a853',
    border: 'none',
    borderRadius: 8,
    color: '#0f1117',
    fontWeight: 600,
    fontSize: 14,
    cursor: 'pointer',
  },
  secondaryBtn: {
    padding: '10px 22px',
    background: 'none',
    border: '1px solid #2a2d38',
    borderRadius: 8,
    color: '#8b8fa8',
    fontSize: 14,
    cursor: 'pointer',
  },
}
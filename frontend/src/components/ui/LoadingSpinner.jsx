/**
 * FIX [FE-04]: Used during auth initialization to prevent the flash of
 * the login page that occurred before the auth state was determined.
 */
export default function LoadingSpinner({ fullScreen = false, message = '' }) {
  if (fullScreen) {
    return (
      <div style={styles.fullScreen}>
        <div style={styles.spinnerLg} />
        {message && <p style={styles.message}>{message}</p>}
      </div>
    )
  }
  return <div style={styles.spinner} />
}

const spin = `
  @keyframes spin { to { transform: rotate(360deg); } }
`

// Inject keyframes once
if (typeof document !== 'undefined') {
  const styleEl = document.createElement('style')
  styleEl.textContent = spin
  document.head.appendChild(styleEl)
}

const styles = {
  fullScreen: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: '#0f1117',
    gap: 16,
  },
  spinnerLg: {
    width: 40,
    height: 40,
    border: '3px solid #2a2d38',
    borderTop: '3px solid #d4a853',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  spinner: {
    width: 24,
    height: 24,
    border: '2px solid #2a2d38',
    borderTop: '2px solid #d4a853',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  message: {
    color: '#8b8fa8',
    fontSize: 14,
    margin: 0,
  },
}


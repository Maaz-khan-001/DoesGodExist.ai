import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authAPI } from '../services/api'
 
const STAGES = {
  FORM:    'form',
  SUCCESS: 'success',
  ERROR:   'error',
}
 
export default function ForgotPasswordPage() {
  const [email, setEmail]   = useState('')
  const [stage, setStage]   = useState(STAGES.FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError]   = useState('')
 
  const isValidEmail = (val) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val)
 
  const handleSubmit = async () => {
    setError('')
 
    if (!email.trim()) {
      setError('Please enter your email address.')
      return
    }
    if (!isValidEmail(email)) {
      setError('Please enter a valid email address.')
      return
    }
 
    setLoading(true)
    try {
      await authAPI.requestPasswordReset(email.trim())
      setStage(STAGES.SUCCESS)
    } catch (err) {
      const msg = err.response?.data?.email?.[0]
        || err.response?.data?.error
        || 'Something went wrong. Please try again.'
      setError(msg)
      setStage(STAGES.ERROR)
    } finally {
      setLoading(false)
    }
  }
 
  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSubmit()
  }
 
  return (
    <div style={styles.page}>
      <div style={styles.card}>
 
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.icon}>🔑</div>
          <h1 style={styles.title}>Reset Password</h1>
          <p style={styles.subtitle}>
            {stage === STAGES.SUCCESS
              ? "Check your inbox"
              : "Enter your email and we'll send you a reset link"}
          </p>
        </div>
 
        {/* ── Step 1: Email form ── */}
        {stage === STAGES.FORM && (
          <div style={styles.body}>
            <label style={styles.label} htmlFor="email">Email address</label>
            <input
              id="email"
              type="email"
              style={styles.input(!!error)}
              placeholder="you@example.com"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError('') }}
              onKeyDown={handleKeyDown}
              autoComplete="email"
              autoFocus
              disabled={loading}
            />
 
            {error && <p style={styles.errorText}>{error}</p>}
 
            <button
              style={styles.btn(loading || !email.trim())}
              onClick={handleSubmit}
              disabled={loading || !email.trim()}
            >
              {loading ? 'Sending…' : 'Send Reset Link'}
            </button>
          </div>
        )}
 
        {/* ── Step 2: Success ── */}
        {stage === STAGES.SUCCESS && (
          <div style={styles.body}>
            <div style={styles.successBox}>
              <div style={styles.successIcon}>✉️</div>
              <p style={styles.successText}>
                We've sent a password reset link to:
              </p>
              <p style={styles.successEmail}>{email}</p>
              <p style={styles.successHint}>
                The link expires in 24 hours. Check your spam folder if you
                don't see it within a few minutes.
              </p>
            </div>
 
            <button
              style={styles.btn(false)}
              onClick={() => { setEmail(''); setStage(STAGES.FORM); setError('') }}
            >
              Send to a different email
            </button>
          </div>
        )}
 
        {/* ── Step 3: Error state ── */}
        {stage === STAGES.ERROR && (
          <div style={styles.body}>
            <div style={styles.errorBox}>
              <p style={styles.errorBoxText}>{error}</p>
            </div>
            <button
              style={styles.btn(false)}
              onClick={() => { setStage(STAGES.FORM); setError('') }}
            >
              Try again
            </button>
          </div>
        )}
 
        {/* Footer */}
        <div style={styles.footer}>
          <Link to="/login" style={styles.link}>← Back to Sign In</Link>
        </div>
 
      </div>
    </div>
  )
}
 
/* ── Styles ─────────────────────────────────────────────────────────────── */
 
const styles = {
  page: {
    minHeight: '100vh',
    background: '#0f1117',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 16px',
  },
  card: {
    width: '100%',
    maxWidth: 400,
    background: '#13151e',
    border: '1px solid #2a2d38',
    borderRadius: 16,
    overflow: 'hidden',
  },
  header: {
    textAlign: 'center',
    padding: '32px 32px 16px',
    borderBottom: '1px solid #2a2d38',
  },
  icon: {
    fontSize: 40,
    marginBottom: 12,
  },
  title: {
    color: '#e8e9ef',
    fontSize: 22,
    fontWeight: 700,
    margin: '0 0 6px',
  },
  subtitle: {
    color: '#8b8fa8',
    fontSize: 14,
    margin: 0,
    lineHeight: 1.5,
  },
  body: {
    padding: '24px 32px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  label: {
    color: '#8b8fa8',
    fontSize: 13,
    fontWeight: 500,
    marginBottom: 4,
  },
  input: (hasError) => ({
    padding: '11px 14px',
    background: '#0f1117',
    border: `1px solid ${hasError ? '#c0392b' : '#2a2d38'}`,
    borderRadius: 8,
    color: '#e8e9ef',
    fontSize: 15,
    outline: 'none',
    transition: 'border-color 0.2s',
    width: '100%',
    boxSizing: 'border-box',
  }),
  errorText: {
    color: '#c0392b',
    fontSize: 13,
    margin: 0,
  },
  btn: (disabled) => ({
    padding: '12px',
    background: disabled ? '#2a2d38' : '#d4a853',
    border: 'none',
    borderRadius: 8,
    color: disabled ? '#555' : '#0f1117',
    fontSize: 15,
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'background 0.2s',
    marginTop: 4,
  }),
  successBox: {
    background: '#1a2e1a',
    border: '1px solid #2d5a2d',
    borderRadius: 10,
    padding: '20px',
    textAlign: 'center',
  },
  successIcon: { fontSize: 36, marginBottom: 12 },
  successText: { color: '#8b8fa8', fontSize: 14, margin: '0 0 6px' },
  successEmail: {
    color: '#d4a853',
    fontSize: 15,
    fontWeight: 600,
    margin: '0 0 10px',
    wordBreak: 'break-all',
  },
  successHint: {
    color: '#555',
    fontSize: 12,
    margin: 0,
    lineHeight: 1.5,
  },
  errorBox: {
    background: '#2e1a1a',
    border: '1px solid #5a2d2d',
    borderRadius: 10,
    padding: '16px',
  },
  errorBoxText: { color: '#e07070', fontSize: 14, margin: 0 },
  footer: {
    borderTop: '1px solid #2a2d38',
    padding: '16px 32px',
    textAlign: 'center',
  },
  link: {
    color: '#8b8fa8',
    textDecoration: 'none',
    fontSize: 14,
  },
}
 
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
 
const MODES = { LOGIN: 'login', REGISTER: 'register' }
 
export default function AuthPage() {
  const { login, register, googleLogin } = useAuth()
  const location = useLocation()
 
  const [mode,       setMode]     = useState(MODES.LOGIN)
  const [email,      setEmail]    = useState('')
  const [password,   setPassword] = useState('')
  const [password2,  setPass2]    = useState('')
  const [loading,    setLoading]  = useState(false)
  const [error,      setError]    = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
 
  // Success message passed from PasswordResetConfirmPage after redirect
  const successMessage = location.state?.message || ''
 
  const clearErrors = () => { setError(''); setFieldErrors({}) }
 
  const validate = () => {
    const errs = {}
    if (!email.trim())    errs.email    = 'Email is required'
    if (!password.trim()) errs.password = 'Password is required'
    if (mode === MODES.REGISTER && password !== password2) {
      errs.password2 = 'Passwords do not match'
    }
    setFieldErrors(errs)
    return Object.keys(errs).length === 0
  }
 
  const handleSubmit = async () => {
    clearErrors()
    if (!validate()) return
    setLoading(true)
    try {
      if (mode === MODES.LOGIN) {
        await login(email.trim(), password)
      } else {
        await register(email.trim(), password, password2)
      }
      // Auth redirect handled by AuthRoute in App.jsx
    } catch (err) {
      const data = err.response?.data
      if (data?.email)     setFieldErrors((p) => ({ ...p, email:    data.email[0]    }))
      if (data?.password1) setFieldErrors((p) => ({ ...p, password: data.password1[0] }))
      if (data?.non_field_errors) setError(data.non_field_errors[0])
      else if (data?.error) setError(data.error)
      else setError('Something went wrong. Please try again.')
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
          <div style={styles.logoIcon}>☽</div>
          <h1 style={styles.title}>DoesGodExist.ai</h1>
          <p style={styles.subtitle}>
            {mode === MODES.LOGIN ? 'Welcome back' : 'Create a free account'}
          </p>
        </div>
 
        <div style={styles.body}>
 
          {/* Success message (e.g. after password reset) */}
          {successMessage && (
            <div style={styles.successBanner}>{successMessage}</div>
          )}
 
          {/* Mode toggle */}
          <div style={styles.tabRow}>
            <button
              style={styles.tab(mode === MODES.LOGIN)}
              onClick={() => { setMode(MODES.LOGIN); clearErrors() }}
            >Sign In</button>
            <button
              style={styles.tab(mode === MODES.REGISTER)}
              onClick={() => { setMode(MODES.REGISTER); clearErrors() }}
            >Register</button>
          </div>
 
          {/* Email */}
          <div style={styles.field}>
            <label style={styles.label}>Email</label>
            <input
              type="email"
              style={styles.input(!!fieldErrors.email)}
              value={email}
              onChange={(e) => { setEmail(e.target.value); clearErrors() }}
              onKeyDown={handleKeyDown}
              placeholder="you@example.com"
              autoComplete="email"
              autoFocus
            />
            {fieldErrors.email && <span style={styles.fieldErr}>{fieldErrors.email}</span>}
          </div>
 
          {/* Password */}
          <div style={styles.field}>
            <div style={styles.labelRow}>
              <label style={styles.label}>Password</label>
              {mode === MODES.LOGIN && (
                <Link to="/forgot-password" style={styles.forgotLink}>
                  Forgot password?
                </Link>
              )}
            </div>
            <input
              type="password"
              style={styles.input(!!fieldErrors.password)}
              value={password}
              onChange={(e) => { setPassword(e.target.value); clearErrors() }}
              onKeyDown={handleKeyDown}
              placeholder={mode === MODES.LOGIN ? '••••••••' : 'Min 8 characters'}
              autoComplete={mode === MODES.LOGIN ? 'current-password' : 'new-password'}
            />
            {fieldErrors.password && <span style={styles.fieldErr}>{fieldErrors.password}</span>}
          </div>
 
          {/* Confirm password (register only) */}
          {mode === MODES.REGISTER && (
            <div style={styles.field}>
              <label style={styles.label}>Confirm Password</label>
              <input
                type="password"
                style={styles.input(!!fieldErrors.password2)}
                value={password2}
                onChange={(e) => { setPass2(e.target.value); clearErrors() }}
                onKeyDown={handleKeyDown}
                placeholder="Repeat password"
                autoComplete="new-password"
              />
              {fieldErrors.password2 && (
                <span style={styles.fieldErr}>{fieldErrors.password2}</span>
              )}
            </div>
          )}
 
          {/* Global error */}
          {error && <div style={styles.errorBanner}>{error}</div>}
 
          {/* Submit */}
          <button
            style={styles.submitBtn(loading)}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading
              ? (mode === MODES.LOGIN ? 'Signing in…' : 'Creating account…')
              : (mode === MODES.LOGIN ? 'Sign In'     : 'Create Account')}
          </button>
 
          {/* Divider */}
          <div style={styles.divider}>
            <div style={styles.dividerLine} />
            <span style={styles.dividerText}>or</span>
            <div style={styles.dividerLine} />
          </div>
 
          {/* Continue without account */}
          <Link to="/" style={styles.guestLink}>
            Continue without an account →
          </Link>
          <p style={styles.guestHint}>5 free turns · no account required</p>
 
        </div>
      </div>
    </div>
  )
}
 
const styles = {
  page: {
    minHeight: '100vh', background: '#0f1117',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    padding: '24px 16px',
  },
  card: {
    width: '100%', maxWidth: 400,
    background: '#13151e', border: '1px solid #2a2d38', borderRadius: 16,
    overflow: 'hidden',
  },
  header: {
    textAlign: 'center', padding: '28px 28px 16px',
    borderBottom: '1px solid #2a2d38',
  },
  logoIcon:  { fontSize: 36, color: '#d4a853', display: 'block', marginBottom: 6 },
  title:     { color: '#d4a853', fontSize: 20, fontWeight: 700, margin: '0 0 4px' },
  subtitle:  { color: '#8b8fa8', fontSize: 14, margin: 0 },
  body:      { padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 14 },
  tabRow:    { display: 'flex', borderRadius: 8, overflow: 'hidden', border: '1px solid #2a2d38' },
  tab: (active) => ({
    flex: 1, padding: '9px', border: 'none',
    background: active ? '#d4a853' : 'transparent',
    color: active ? '#0f1117' : '#8b8fa8',
    cursor: 'pointer', fontWeight: active ? 600 : 400, fontSize: 14,
    transition: 'background 0.2s',
  }),
  field:     { display: 'flex', flexDirection: 'column', gap: 4 },
  labelRow:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  label:     { color: '#8b8fa8', fontSize: 13, fontWeight: 500 },
  forgotLink: { color: '#8b8fa8', fontSize: 12, textDecoration: 'none' },
  input: (err) => ({
    padding: '10px 12px', background: '#0f1117',
    border: `1px solid ${err ? '#c0392b' : '#2a2d38'}`,
    borderRadius: 8, color: '#e8e9ef', fontSize: 15, outline: 'none',
  }),
  fieldErr:   { color: '#c0392b', fontSize: 12 },
  errorBanner: {
    background: '#2e1a1a', border: '1px solid #5a2d2d',
    borderRadius: 8, padding: '10px 12px',
    color: '#e07070', fontSize: 13,
  },
  successBanner: {
    background: '#1a2e1a', border: '1px solid #2d5a2d',
    borderRadius: 8, padding: '10px 12px',
    color: '#6dbf6d', fontSize: 13,
  },
  submitBtn: (loading) => ({
    padding: '12px', background: loading ? '#2a2d38' : '#d4a853',
    border: 'none', borderRadius: 8,
    color: loading ? '#555' : '#0f1117',
    fontSize: 15, fontWeight: 600,
    cursor: loading ? 'not-allowed' : 'pointer',
  }),
  divider: {
    display: 'flex', alignItems: 'center', gap: 10,
  },
  dividerLine: { flex: 1, height: 1, background: '#2a2d38' },
  dividerText: { color: '#555', fontSize: 12 },
  guestLink: {
    textAlign: 'center', color: '#d4a853',
    textDecoration: 'none', fontSize: 14, fontWeight: 500,
  },
  guestHint: { textAlign: 'center', color: '#555', fontSize: 12, margin: 0 },
}
 
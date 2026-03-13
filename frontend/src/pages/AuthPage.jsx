import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { Loader2, Mail, Lock, Eye, EyeOff, ArrowRight } from 'lucide-react'

const MODES = { LOGIN: 'login', REGISTER: 'register' }

/**
 * IMPROVED AUTHPAGE
 * 
 * Changes:
 * - Updated to teal accent color
 * - Improved form styling with icons
 * - Password visibility toggle
 * - Better error/success states
 * - Improved loading states
 * - Better responsive design
 * - Accessibility improvements
 * - NO NAVBAR (as requested)
 */
export default function AuthPage() {
  const { login, register } = useAuth()
  const location = useLocation()

  const [mode, setMode] = useState(MODES.LOGIN)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [password2, setPass2] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [showPassword2, setShowPassword2] = useState(false)

  // Success message passed from PasswordResetConfirmPage after redirect
  const successMessage = location.state?.message || ''

  const clearErrors = () => { setError(''); setFieldErrors({}) }

  const validate = () => {
    const errs = {}
    if (!email.trim()) errs.email = 'Email is required'
    if (!password.trim()) errs.password = 'Password is required'
    if (mode === MODES.REGISTER && password !== password2) {
      errs.password2 = 'Passwords do not match'
    }
    if (mode === MODES.REGISTER && password.length < 8) {
      errs.password = 'Password must be at least 8 characters'
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
      if (data?.email) setFieldErrors((p) => ({ ...p, email: data.email[0] }))
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
            {mode === MODES.LOGIN ? 'Welcome back' : 'Create your account'}
          </p>
        </div>

        <div style={styles.body}>
          {/* Success message */}
          {successMessage && (
            <div style={styles.successBanner} role="alert">
              {successMessage}
            </div>
          )}

          {/* Mode toggle */}
          <div style={styles.tabRow} role="tablist" aria-label="Authentication mode">
            <button
              style={styles.tab(mode === MODES.LOGIN)}
              onClick={() => { setMode(MODES.LOGIN); clearErrors() }}
              role="tab"
              aria-selected={mode === MODES.LOGIN}
            >
              Sign In
            </button>
            <button
              style={styles.tab(mode === MODES.REGISTER)}
              onClick={() => { setMode(MODES.REGISTER); clearErrors() }}
              role="tab"
              aria-selected={mode === MODES.REGISTER}
            >
              Register
            </button>
          </div>

          {/* Email */}
          <div style={styles.field}>
            <label style={styles.label} htmlFor="email">Email</label>
            <div style={styles.inputWrapper(!!fieldErrors.email)}>
              <Mail size={18} style={styles.inputIcon} />
              <input
                id="email"
                type="email"
                style={styles.input}
                value={email}
                onChange={(e) => { setEmail(e.target.value); clearErrors() }}
                onKeyDown={handleKeyDown}
                placeholder="you@example.com"
                autoComplete="email"
                autoFocus
                aria-invalid={!!fieldErrors.email}
                aria-describedby={fieldErrors.email ? 'email-error' : undefined}
              />
            </div>
            {fieldErrors.email && (
              <span id="email-error" style={styles.fieldErr} role="alert">
                {fieldErrors.email}
              </span>
            )}
          </div>

          {/* Password */}
          <div style={styles.field}>
            <div style={styles.labelRow}>
              <label style={styles.label} htmlFor="password">Password</label>
              {mode === MODES.LOGIN && (
                <Link to="/forgot-password" style={styles.forgotLink}>
                  Forgot password?
                </Link>
              )}
            </div>
            <div style={styles.inputWrapper(!!fieldErrors.password)}>
              <Lock size={18} style={styles.inputIcon} />
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                style={styles.input}
                value={password}
                onChange={(e) => { setPassword(e.target.value); clearErrors() }}
                onKeyDown={handleKeyDown}
                placeholder={mode === MODES.LOGIN ? '••••••••' : 'Min 8 characters'}
                autoComplete={mode === MODES.LOGIN ? 'current-password' : 'new-password'}
                aria-invalid={!!fieldErrors.password}
                aria-describedby={fieldErrors.password ? 'password-error' : undefined}
              />
              <button
                type="button"
                style={styles.eyeBtn}
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
            {fieldErrors.password && (
              <span id="password-error" style={styles.fieldErr} role="alert">
                {fieldErrors.password}
              </span>
            )}
          </div>

          {/* Confirm password (register only) */}
          {mode === MODES.REGISTER && (
            <div style={styles.field}>
              <label style={styles.label} htmlFor="password2">Confirm Password</label>
              <div style={styles.inputWrapper(!!fieldErrors.password2)}>
                <Lock size={18} style={styles.inputIcon} />
                <input
                  id="password2"
                  type={showPassword2 ? 'text' : 'password'}
                  style={styles.input}
                  value={password2}
                  onChange={(e) => { setPass2(e.target.value); clearErrors() }}
                  onKeyDown={handleKeyDown}
                  placeholder="Repeat password"
                  autoComplete="new-password"
                  aria-invalid={!!fieldErrors.password2}
                  aria-describedby={fieldErrors.password2 ? 'password2-error' : undefined}
                />
                <button
                  type="button"
                  style={styles.eyeBtn}
                  onClick={() => setShowPassword2(!showPassword2)}
                  aria-label={showPassword2 ? 'Hide password' : 'Show password'}
                >
                  {showPassword2 ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
              {fieldErrors.password2 && (
                <span id="password2-error" style={styles.fieldErr} role="alert">
                  {fieldErrors.password2}
                </span>
              )}
            </div>
          )}

          {/* Global error */}
          {error && (
            <div style={styles.errorBanner} role="alert">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            style={styles.submitBtn(loading)}
            onClick={handleSubmit}
            disabled={loading}
            aria-busy={loading}
          >
            {loading ? (
              <>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                {mode === MODES.LOGIN ? 'Signing in...' : 'Creating account...'}
              </>
            ) : (
              <>
                {mode === MODES.LOGIN ? 'Sign In' : 'Create Account'}
                <ArrowRight size={18} />
              </>
            )}
          </button>

          {/* Divider */}
          <div style={styles.divider}>
            <div style={styles.dividerLine} />
            <span style={styles.dividerText}>or</span>
            <div style={styles.dividerLine} />
          </div>

          {/* Continue without account */}
          <Link to="/" style={styles.guestLink}>
            Continue without an account
            <ArrowRight size={16} />
          </Link>
          <p style={styles.guestHint}>5 free turns · no account required</p>
        </div>
      </div>

      {/* Footer */}
      <p style={styles.footer}>
        By continuing, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  page: {
    minHeight: '100vh',
    background: 'var(--bg-primary)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px 16px',
  },
  card: {
    width: '100%',
    maxWidth: 420,
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    overflow: 'hidden',
    boxShadow: 'var(--shadow-lg)',
  },
  header: {
    textAlign: 'center',
    padding: '32px 32px 20px',
    borderBottom: '1px solid var(--border-primary)',
  },
  logoIcon: {
    fontSize: 40,
    color: 'var(--accent-primary)',
    display: 'block',
    marginBottom: 12,
  },
  title: {
    color: 'var(--accent-primary)',
    fontSize: 22,
    fontWeight: 700,
    margin: '0 0 6px',
  },
  subtitle: {
    color: 'var(--text-muted)',
    fontSize: 14,
    margin: 0,
  },
  body: {
    padding: '28px 32px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  successBanner: {
    background: 'var(--success-bg)',
    border: '1px solid var(--success)',
    borderRadius: 'var(--radius-md)',
    padding: '12px 16px',
    color: 'var(--success)',
    fontSize: 13,
    textAlign: 'center',
  },
  tabRow: {
    display: 'flex',
    borderRadius: 'var(--radius-md)',
    overflow: 'hidden',
    border: '1px solid var(--border-primary)',
    background: 'var(--bg-tertiary)',
  },
  tab: (active) => ({
    flex: 1,
    padding: '12px',
    border: 'none',
    background: active ? 'var(--accent-primary)' : 'transparent',
    color: active ? 'var(--bg-primary)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontWeight: active ? 600 : 400,
    fontSize: 14,
    transition: 'all var(--transition-fast)',
  }),
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  labelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  label: {
    color: 'var(--text-muted)',
    fontSize: 13,
    fontWeight: 500,
  },
  forgotLink: {
    color: 'var(--accent-primary)',
    fontSize: 12,
    textDecoration: 'none',
    transition: 'opacity var(--transition-fast)',
  },
  inputWrapper: (hasError) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 14px',
    background: 'var(--bg-primary)',
    border: `1px solid ${hasError ? 'var(--error)' : 'var(--border-primary)'}`,
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  }),
  inputIcon: {
    color: 'var(--text-muted)',
    flexShrink: 0,
  },
  input: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: 15,
    outline: 'none',
    fontFamily: 'inherit',
  },
  eyeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'color var(--transition-fast)',
  },
  fieldErr: {
    color: 'var(--error)',
    fontSize: 12,
  },
  errorBanner: {
    background: 'var(--error-bg)',
    border: '1px solid var(--error)',
    borderRadius: 'var(--radius-md)',
    padding: '12px 16px',
    color: 'var(--error)',
    fontSize: 13,
    textAlign: 'center',
  },
  submitBtn: (loading) => ({
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    padding: '14px',
    background: loading ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: loading ? 'var(--text-muted)' : 'var(--bg-primary)',
    fontSize: 15,
    fontWeight: 600,
    cursor: loading ? 'not-allowed' : 'pointer',
    transition: 'all var(--transition-fast)',
  }),
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    margin: '4px 0',
  },
  dividerLine: {
    flex: 1,
    height: 1,
    background: 'var(--border-primary)',
  },
  dividerText: {
    color: 'var(--text-disabled)',
    fontSize: 12,
  },
  guestLink: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    color: 'var(--accent-primary)',
    textDecoration: 'none',
    fontSize: 14,
    fontWeight: 500,
    padding: '12px',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-md)',
    transition: 'all var(--transition-fast)',
  },
  guestHint: {
    textAlign: 'center',
    color: 'var(--text-disabled)',
    fontSize: 12,
    margin: '-8px 0 0',
  },
  footer: {
    marginTop: 24,
    color: 'var(--text-muted)',
    fontSize: 12,
    textAlign: 'center',
    maxWidth: 360,
  },
}

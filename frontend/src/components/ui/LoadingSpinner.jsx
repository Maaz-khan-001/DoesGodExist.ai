import { Loader2 } from 'lucide-react'

/**
 * IMPROVED LOADINGSPIINNER
 * 
 * Changes:
 * - Updated to teal accent color
 * - Uses Lucide icon for consistency
 * - Better sizing options
 * - Accessibility improvements
 */
export default function LoadingSpinner({ 
  fullScreen = false, 
  message = '',
  size = 'md'
}) {
  const sizeMap = {
    sm: 20,
    md: 32,
    lg: 48,
    xl: 64,
  }
  
  const spinnerSize = sizeMap[size] || sizeMap.md

  if (fullScreen) {
    return (
      <div 
        style={styles.fullScreen}
        role="status"
        aria-live="polite"
        aria-label={message || 'Loading'}
      >
        <Loader2 
          size={spinnerSize} 
          style={{ 
            animation: 'spin 1s linear infinite',
            color: 'var(--accent-primary)'
          }} 
        />
        {message && <p style={styles.message}>{message}</p>}
      </div>
    )
  }

  return (
    <div 
      style={styles.inline}
      role="status"
      aria-label="Loading"
    >
      <Loader2 
        size={spinnerSize} 
        style={{ 
          animation: 'spin 1s linear infinite',
          color: 'var(--accent-primary)'
        }} 
      />
    </div>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  fullScreen: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: 'var(--bg-primary)',
    gap: 16,
  },
  inline: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  message: {
    color: 'var(--text-muted)',
    fontSize: 14,
    margin: 0,
  },
}

import { AlertTriangle } from 'lucide-react'

/**
 * IMPROVED MODAL
 * 
 * Changes:
 * - Updated to teal accent color
 * - Better visual hierarchy
 * - Improved button styling
 * - Added icon for destructive actions
 * - Better spacing and typography
 * - Accessibility improvements
 */
export default function Modal({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
  destructive = false,
}) {
  if (!isOpen) return null

  return (
    <div 
      style={styles.overlay} 
      onClick={onCancel}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-message"
    >
      <div 
        style={styles.modal} 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon for destructive actions */}
        {destructive && (
          <div style={styles.iconWrapper}>
            <AlertTriangle size={28} style={{ color: 'var(--error)' }} />
          </div>
        )}

        {/* Title */}
        <h3 id="modal-title" style={styles.title}>
          {title}
        </h3>

        {/* Message */}
        <p id="modal-message" style={styles.message}>
          {message}
        </p>

        {/* Buttons */}
        <div style={styles.buttons}>
          <button 
            style={styles.cancelBtn} 
            onClick={onCancel}
          >
            {cancelLabel}
          </button>
          <button
            style={styles.confirmBtn(destructive)}
            onClick={onConfirm}
            autoFocus
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.7)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '16px',
    animation: 'fadeIn var(--transition-fast)',
  },
  modal: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    padding: '28px',
    maxWidth: 400,
    width: '100%',
    textAlign: 'center',
    boxShadow: 'var(--shadow-lg)',
    animation: 'fadeIn var(--transition-base)',
  },
  iconWrapper: {
    width: 56,
    height: 56,
    borderRadius: '50%',
    background: 'var(--error-bg)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
  },
  title: {
    color: 'var(--text-primary)',
    fontSize: 18,
    fontWeight: 600,
    margin: '0 0 12px',
  },
  message: {
    color: 'var(--text-muted)',
    fontSize: 14,
    margin: '0 0 24px',
    lineHeight: 1.6,
  },
  buttons: {
    display: 'flex',
    gap: 12,
    justifyContent: 'center',
  },
  cancelBtn: {
    padding: '10px 20px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-secondary)',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
  },
  confirmBtn: (destructive) => ({
    padding: '10px 20px',
    background: destructive ? 'var(--error)' : 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: '#fff',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
    transition: 'all var(--transition-fast)',
  }),
}

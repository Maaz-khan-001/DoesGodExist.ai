/**
 * Simple confirmation modal.
 * Used for session deletion confirmation.
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
    <div style={styles.overlay} onClick={onCancel}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <h3 style={styles.title}>{title}</h3>
        <p style={styles.message}>{message}</p>
        <div style={styles.buttons}>
          <button style={styles.cancelBtn} onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            style={styles.confirmBtn(destructive)}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

const styles = {
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 200,
  },
  modal: {
    background: '#1a1d24',
    border: '1px solid #2a2d38',
    borderRadius: 12,
    padding: '24px',
    maxWidth: 360,
    width: '90%',
  },
  title: {
    color: '#e8e9ef',
    fontSize: 16,
    fontWeight: 600,
    margin: '0 0 8px',
  },
  message: {
    color: '#8b8fa8',
    fontSize: 14,
    margin: '0 0 20px',
    lineHeight: 1.5,
  },
  buttons: {
    display: 'flex',
    gap: 8,
    justifyContent: 'flex-end',
  },
  cancelBtn: {
    padding: '8px 16px',
    background: 'none',
    border: '1px solid #2a2d38',
    borderRadius: 8,
    color: '#8b8fa8',
    cursor: 'pointer',
    fontSize: 13,
  },
  confirmBtn: (destructive) => ({
    padding: '8px 16px',
    background: destructive ? '#8b2020' : '#d4a853',
    border: 'none',
    borderRadius: 8,
    color: destructive ? '#fff' : '#0f1117',
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 600,
  }),
}

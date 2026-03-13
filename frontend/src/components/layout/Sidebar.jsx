import { useState } from 'react'
import useDebateStore from '../../store/debateStore'
import { debateAPI } from '../../services/api'
import { useAuth } from '../../hooks/useAuth'
import Modal from '../ui/Modal'
import { 
  X, 
  Plus, 
  Trash2, 
  MessageSquare, 
  Heart,
  Loader2,
  History
} from 'lucide-react'

/**
 * IMPROVED SIDEBAR
 * 
 * Changes:
 * - Updated to teal accent color
 * - Improved session item styling
 * - Better loading states
 * - Improved empty state
 * - Better delete confirmation
 * - Accessibility improvements
 */
export default function Sidebar({ isOpen, onClose, onNewSession }) {
  const { isAuthenticated } = useAuth()
  const {
    sessionHistory,
    removeSessionFromHistory,
    currentSessionId,
    loadSession,
  } = useDebateStore()

  const [loadingSessionId, setLoadingSessionId] = useState(null)
  const [deletingSessionId, setDeletingSessionId] = useState(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)

  const STAGE_LABELS = {
    existence:   'Existence of God',
    prophethood: 'Prophethood',
    muhammad:    'Muhammad ﷺ',
    invitation:  'Invitation to Islam',
  }

  const handleSessionClick = async (session) => {
    if (session.id === currentSessionId) {
      onClose()
      return
    }

    setLoadingSessionId(session.id)
    try {
      const { data: fullSession } = await debateAPI.getSession(session.id)
      loadSession(fullSession)
      onClose()
    } catch (err) {
      console.error('Failed to load session:', err)
    } finally {
      setLoadingSessionId(null)
    }
  }

  const handleNewSession = () => {
    onNewSession()
    onClose()
  }

  const handleDeleteClick = (e, sessionId) => {
    e.stopPropagation()
    setConfirmDeleteId(sessionId)
  }

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return
    setDeletingSessionId(confirmDeleteId)
    setConfirmDeleteId(null)

    try {
      await debateAPI.deleteSession(confirmDeleteId)
      removeSessionFromHistory(confirmDeleteId)
    } catch (err) {
      console.error('Failed to delete session:', err)
    } finally {
      setDeletingSessionId(null)
    }
  }

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          style={styles.overlay} 
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside 
        style={styles.sidebar(isOpen)}
        role="complementary"
        aria-label="Session sidebar"
      >
        {/* Header */}
        <div style={styles.header}>
          <span style={styles.logo}>
            <MessageSquare size={18} />
            DoesGodExist.ai
          </span>
          <button 
            style={styles.closeBtn} 
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <X size={20} />
          </button>
        </div>

        {/* New debate button */}
        <button style={styles.newBtn} onClick={handleNewSession}>
          <Plus size={18} />
          <span>New Debate</span>
        </button>

        {/* Session history */}
        <div style={styles.historySection}>
          <p style={styles.historyLabel}>
            <History size={14} />
            {isAuthenticated ? 'Your Debates' : 'Sign in to save debates'}
          </p>

          {sessionHistory.length === 0 && isAuthenticated && (
            <div style={styles.emptyState}>
              <MessageSquare size={32} style={{ opacity: 0.3 }} />
              <p style={styles.emptyText}>No debates yet</p>
              <p style={styles.emptySubtext}>Start a new conversation!</p>
            </div>
          )}

          {!isAuthenticated && (
            <div style={styles.emptyState}>
              <History size={32} style={{ opacity: 0.3 }} />
              <p style={styles.emptyText}>Guest mode</p>
              <p style={styles.emptySubtext}>Sign in to save your debates</p>
            </div>
          )}

          <div style={styles.sessionList} role="list">
            {sessionHistory.map((session) => (
              <div
                key={session.id}
                style={styles.sessionItem(session.id === currentSessionId)}
                onClick={() => handleSessionClick(session)}
                role="listitem"
                aria-current={session.id === currentSessionId ? 'true' : undefined}
              >
                <div style={styles.sessionContent}>
                  <p style={styles.sessionTitle}>
                    {loadingSessionId === session.id ? (
                      <span style={styles.loadingText}>
                        <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                        Loading...
                      </span>
                    ) : (
                      session.title || 'Debate Session'
                    )}
                  </p>
                  <p style={styles.sessionMeta}>
                    {STAGE_LABELS[session.current_stage] || session.current_stage}
                    {session.total_turns > 0 && ` · ${session.total_turns} turns`}
                  </p>
                </div>

                {/* Delete button */}
                <button
                  style={styles.deleteBtn(deletingSessionId === session.id)}
                  onClick={(e) => handleDeleteClick(e, session.id)}
                  disabled={deletingSessionId === session.id}
                  title="Delete this debate"
                  aria-label="Delete debate"
                >
                  {deletingSessionId === session.id ? (
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom links */}
        <div style={styles.footer}>
          <a
            href="https://stripe.com"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.supportBtn}
          >
            <Heart size={14} />
            Support this project
          </a>
        </div>
      </aside>

      {/* Confirm delete modal */}
      <Modal
        isOpen={!!confirmDeleteId}
        title="Delete Debate?"
        message="This debate and all its messages will be permanently deleted. This action cannot be undone."
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDeleteId(null)}
        destructive
      />
    </>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0, 0, 0, 0.5)',
    backdropFilter: 'blur(2px)',
    zIndex: 99,
  },
  sidebar: (isOpen) => ({
    position: 'fixed',
    left: 0,
    top: 0,
    bottom: 0,
    width: 300,
    background: 'var(--bg-secondary)',
    borderRight: '1px solid var(--border-primary)',
    display: 'flex',
    flexDirection: 'column',
    transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
    transition: 'transform var(--transition-base)',
    zIndex: 100,
    overflowY: 'auto',
  }),
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px',
    borderBottom: '1px solid var(--border-primary)',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    color: 'var(--accent-primary)',
    fontWeight: 600,
    fontSize: 15,
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    padding: '8px',
    borderRadius: 'var(--radius-md)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all var(--transition-fast)',
  },
  newBtn: {
    margin: 12,
    padding: '12px 16px',
    background: 'var(--accent-primary)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    color: 'var(--bg-primary)',
    fontWeight: 600,
    cursor: 'pointer',
    fontSize: 14,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    transition: 'all var(--transition-fast)',
  },
  historySection: {
    flex: 1,
    padding: '0 12px',
    overflowY: 'auto',
  },
  historyLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--text-disabled)',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: 1,
    padding: '12px 8px 8px',
    margin: 0,
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '40px 20px',
    color: 'var(--text-muted)',
    textAlign: 'center',
  },
  emptyText: {
    fontSize: 14,
    fontWeight: 500,
    margin: '12px 0 4px',
    color: 'var(--text-secondary)',
  },
  emptySubtext: {
    fontSize: 12,
    margin: 0,
    color: 'var(--text-muted)',
  },
  sessionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  sessionItem: (isActive) => ({
    display: 'flex',
    alignItems: 'center',
    padding: '12px',
    borderRadius: 'var(--radius-md)',
    cursor: 'pointer',
    background: isActive ? 'var(--accent-dim)' : 'transparent',
    border: `1px solid ${isActive ? 'var(--accent-primary)' : 'transparent'}`,
    transition: 'all var(--transition-fast)',
  }),
  sessionContent: {
    flex: 1,
    minWidth: 0,
  },
  sessionTitle: {
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 500,
    margin: '0 0 4px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  loadingText: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--text-muted)',
  },
  sessionMeta: {
    color: 'var(--text-muted)',
    fontSize: 11,
    margin: 0,
  },
  deleteBtn: (loading) => ({
    background: 'none',
    border: 'none',
    color: loading ? 'var(--text-disabled)' : 'var(--text-muted)',
    cursor: loading ? 'not-allowed' : 'pointer',
    padding: '6px',
    borderRadius: 'var(--radius-sm)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    opacity: loading ? 0.5 : 0.6,
    transition: 'all var(--transition-fast)',
  }),
  footer: {
    padding: '12px 16px',
    borderTop: '1px solid var(--border-primary)',
  },
  supportBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '10px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--accent-primary)',
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 500,
    transition: 'all var(--transition-fast)',
  },
}

import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import useDebateStore from '../../store/debateStore'


/**
 * FIX [MISS-03]: Logout button was completely absent from UI.
 * The logout function existed in useAuth but was never exposed.
 */
export default function Navbar({ onMenuClick }) {
  const { user, isAuthenticated, logout } = useAuth()
  const { currentStage } = useDebateStore()
  const { streamingEnabled, toggleStreaming } = useDebateStore()

  const STAGE_PROGRESS = {
    existence: 1,
    prophethood: 2,
    muhammad: 3,
    invitation: 4,
  }
  const stageNum = STAGE_PROGRESS[currentStage] || 1

  return (
    <nav style={styles.nav}>
      {/* Left: Hamburger menu (opens sidebar) */}
      <button style={styles.menuBtn} onClick={onMenuClick} title="Open menu">
        ☰
      </button>
      <button
  style={styles.streamToggleBtn(streamingEnabled)}
  onClick={toggleStreaming}
  title={streamingEnabled ? 'Streaming ON — click to disable' : 'Streaming OFF — click to enable'}
>
  {streamingEnabled ? '⚡ Stream' : '⚡ Off'}
</button>

      {/* Center: Logo + stage progress */}
      <div style={styles.center}>
        <span style={styles.logo}>DoesGodExist.ai</span>
        <div style={styles.progressDots}>
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              style={styles.dot(n <= stageNum, n === stageNum)}
              title={['Existence', 'Prophethood', 'Muhammad ﷺ', 'Invitation'][n - 1]}
            />
          ))}
        </div>
      </div>

      {/* Right: User chip + logout OR sign in link */}
      <div style={styles.right}>
        {isAuthenticated ? (
          <div style={styles.userArea}>
            <div style={styles.userChip}>
              <div style={styles.userDot} />
              <span style={styles.userEmail}>
                {user?.email?.split('@')[0] || 'Account'}
              </span>
            </div>
            {/* FIX: Logout button now visible and functional */}
            <button
              style={styles.logoutBtn}
              onClick={logout}
              title="Sign out"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <Link to="/login" style={styles.signInLink}>
            Sign In
          </Link>
        )}
      </div>
    </nav>
  )
}

const styles = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    height: 56,
    background: '#13151e',
    borderBottom: '1px solid #2a2d38',
    flexShrink: 0,
    gap: 12,
  },
  menuBtn: {
    background: 'none',
    border: 'none',
    color: '#8b8fa8',
    fontSize: 20,
    cursor: 'pointer',
    padding: 4,
  },
  center: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  logo: {
    color: '#d4a853',
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: 0.5,
  },
  progressDots: {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
  },
  dot: (completed, current) => ({
    width: current ? 10 : 8,
    height: current ? 10 : 8,
    borderRadius: '50%',
    background: completed ? '#d4a853' : '#2a2d38',
    border: current ? '2px solid #d4a853' : 'none',
    boxShadow: current ? '0 0 6px #d4a853' : 'none',
    transition: 'all 0.3s',
  }),
  right: {
    display: 'flex',
    alignItems: 'center',
  },
  userArea: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  userChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 10px',
    background: '#1e2130',
    borderRadius: 20,
    border: '1px solid #2a2d38',
  },
  userDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: '#4caf50',
  },
  userEmail: {
    color: '#e8e9ef',
    fontSize: 13,
    maxWidth: 100,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  logoutBtn: {
    background: 'none',
    border: '1px solid #2a2d38',
    borderRadius: 6,
    color: '#8b8fa8',
    fontSize: 12,
    padding: '4px 10px',
    cursor: 'pointer',
    transition: 'color 0.15s, border-color 0.15s',
  },
  signInLink: {
    color: '#d4a853',
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 500,
    padding: '6px 12px',
    background: '#1e2130',
    borderRadius: 8,
    border: '1px solid #2a2d38',
  },
  streamToggleBtn: (on) => ({
  padding: '4px 10px',
  background: on ? '#1a2e1a' : '#1e2130',
  border: `1px solid ${on ? '#2d5a2d' : '#2a2d38'}`,
  borderRadius: 6,
  color: on ? '#4caf50' : '#555',
  fontSize: 12,
  cursor: 'pointer',
  fontWeight: on ? 600 : 400,
  transition: 'all 0.2s',
}),
}

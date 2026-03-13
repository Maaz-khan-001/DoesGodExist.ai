import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import useDebateStore from '../../store/debateStore'
import { 
  Menu, 
  Settings, 
  User, 
  LogOut, 
  ChevronDown,
  Zap,
  ZapOff,
  Moon,
  Sun
} from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'

/**
 * IMPROVED NAVBAR
 * 
 * Changes:
 * - Moved Sign Out button to User Profile dropdown
 * - Added Settings icon in top-right
 * - Changed accent color to teal
 * - Improved visual design with better spacing
 * - Added hover states and transitions
 * - Better responsive design
 * - Accessibility improvements
 */
export default function Navbar({ onMenuClick, onSettingsClick }) {
  const { user, isAuthenticated, logout } = useAuth()
  const { currentStage, streamingEnabled, toggleStreaming } = useDebateStore()
  const { isDark, toggleTheme } = useTheme()
  
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef(null)

  const STAGE_PROGRESS = {
    existence: 1,
    prophethood: 2,
    muhammad: 3,
    invitation: 4,
  }
  const stageNum = STAGE_PROGRESS[currentStage] || 1

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Handle logout from dropdown
  const handleLogout = () => {
    setUserMenuOpen(false)
    logout()
  }

  return (
    <nav style={styles.nav} role="banner">
      {/* Left: Hamburger menu + Stream toggle */}
      <div style={styles.left}>
        <button 
          style={styles.iconBtn} 
          onClick={onMenuClick}
          title="Open menu (Ctrl+B)"
          aria-label="Open sidebar menu"
        >
          <Menu size={20} />
        </button>
        
        <button
          style={styles.streamToggleBtn(streamingEnabled)}
          onClick={toggleStreaming}
          title={streamingEnabled ? 'Streaming enabled - click to disable' : 'Streaming disabled - click to enable'}
          aria-pressed={streamingEnabled}
        >
          {streamingEnabled ? <Zap size={14} /> : <ZapOff size={14} />}
          <span>Stream</span>
        </button>
      </div>

      {/* Center: Logo + stage progress */}
      <div style={styles.center}>
        <Link to="/" style={styles.logo} aria-label="DoesGodExist.ai Home">
          <span style={styles.logoIcon}>☽</span>
          <span>DoesGodExist.ai</span>
        </Link>
        <div style={styles.progressDots} aria-label={`Stage ${stageNum} of 4`}>
          {[1, 2, 3, 4].map((n) => (
            <div
              key={n}
              style={styles.dot(n <= stageNum, n === stageNum)}
              title={['Existence', 'Prophethood', 'Muhammad ﷺ', 'Invitation'][n - 1]}
              aria-label={`Stage ${n}: ${['Existence of God', 'Prophethood', 'Muhammad ﷺ', 'Invitation to Islam'][n - 1]} ${n <= stageNum ? '- completed' : n === stageNum ? '- current' : '- upcoming'}`}
            />
          ))}
        </div>
      </div>

      {/* Right: Theme toggle + Settings + User */}
      <div style={styles.right}>
        {/* Theme toggle */}
        <button
          style={styles.iconBtn}
          onClick={toggleTheme}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Settings button */}
        <button
          style={styles.iconBtn}
          onClick={onSettingsClick}
          title="Settings (Ctrl+/)"
          aria-label="Open settings"
        >
          <Settings size={18} />
        </button>

        {/* User menu */}
        {isAuthenticated ? (
          <div style={styles.userMenuContainer} ref={userMenuRef}>
            <button
              style={styles.userChip}
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              aria-expanded={userMenuOpen}
              aria-haspopup="menu"
              aria-label={`User menu for ${user?.email}`}
            >
              <div style={styles.userAvatar}>
                <User size={14} />
              </div>
              <span style={styles.userEmail}>
                {user?.email?.split('@')[0] || 'Account'}
              </span>
              <ChevronDown 
                size={14} 
                style={{ 
                  transform: userMenuOpen ? 'rotate(180deg)' : 'rotate(0)',
                  transition: 'transform var(--transition-fast)',
                  color: 'var(--text-muted)'
                }} 
              />
            </button>

            {/* Dropdown menu */}
            {userMenuOpen && (
              <div 
                style={styles.dropdown}
                role="menu"
                aria-label="User menu"
              >
                <div style={styles.dropdownHeader}>
                  <span style={styles.dropdownEmail}>{user?.email}</span>
                </div>
                <div style={styles.dropdownDivider} />
                <button 
                  style={styles.dropdownItem}
                  onClick={handleLogout}
                  role="menuitem"
                >
                  <LogOut size={16} />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
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

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  nav: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 16px',
    height: 60,
    background: 'var(--bg-secondary)',
    borderBottom: '1px solid var(--border-primary)',
    flexShrink: 0,
    gap: 12,
  },
  left: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  iconBtn: {
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
  streamToggleBtn: (on) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '6px 12px',
    background: on ? 'var(--accent-dim)' : 'var(--bg-tertiary)',
    border: `1px solid ${on ? 'var(--accent-primary)' : 'var(--border-primary)'}`,
    borderRadius: 'var(--radius-md)',
    color: on ? 'var(--accent-primary)' : 'var(--text-muted)',
    fontSize: 12,
    cursor: 'pointer',
    fontWeight: on ? 600 : 400,
    transition: 'all var(--transition-fast)',
  }),
  center: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    color: 'var(--accent-primary)',
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: 0.5,
    textDecoration: 'none',
    transition: 'opacity var(--transition-fast)',
  },
  logoIcon: {
    fontSize: 20,
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
    background: completed ? 'var(--accent-primary)' : 'var(--border-primary)',
    border: current ? '2px solid var(--accent-primary)' : 'none',
    boxShadow: current ? '0 0 8px var(--accent-glow)' : 'none',
    transition: 'all var(--transition-base)',
  }),
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flex: 1,
    justifyContent: 'flex-end',
  },
  userMenuContainer: {
    position: 'relative',
  },
  userChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 12px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-full)',
    border: '1px solid var(--border-primary)',
    color: 'var(--text-primary)',
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all var(--transition-fast)',
  },
  userAvatar: {
    width: 24,
    height: 24,
    borderRadius: '50%',
    background: 'var(--accent-dim)',
    color: 'var(--accent-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  userEmail: {
    maxWidth: 100,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  dropdown: {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    minWidth: 200,
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-lg)',
    boxShadow: 'var(--shadow-lg)',
    zIndex: 100,
    overflow: 'hidden',
    animation: 'fadeIn var(--transition-fast)',
  },
  dropdownHeader: {
    padding: '12px 16px',
    background: 'var(--bg-tertiary)',
  },
  dropdownEmail: {
    color: 'var(--text-muted)',
    fontSize: 12,
    wordBreak: 'break-all',
  },
  dropdownDivider: {
    height: 1,
    background: 'var(--border-primary)',
  },
  dropdownItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    width: '100%',
    padding: '12px 16px',
    background: 'none',
    border: 'none',
    color: 'var(--error)',
    fontSize: 14,
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'background var(--transition-fast)',
  },
  signInLink: {
    color: 'var(--accent-primary)',
    textDecoration: 'none',
    fontSize: 13,
    fontWeight: 500,
    padding: '8px 16px',
    background: 'var(--bg-elevated)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border-primary)',
    transition: 'all var(--transition-fast)',
  },
}

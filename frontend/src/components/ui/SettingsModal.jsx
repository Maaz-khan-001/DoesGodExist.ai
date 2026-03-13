import { useState } from 'react'
import { useTheme } from '../../contexts/ThemeContext'
import { 
  X, 
  Moon, 
  Sun, 
  Monitor, 
  Globe, 
  Bell, 
  Keyboard,
  Palette,
  Check
} from 'lucide-react'

/**
 * SettingsModal
 * 
 * A comprehensive settings panel that includes:
 * - Dark/Light/System theme toggle
 * - Language selector (placeholder for future i18n)
 * - UI preferences
 * - Keyboard shortcuts info
 * - Accessibility options
 */
export default function SettingsModal({ isOpen, onClose }) {
  const { theme, isDark, isLight, isSystemPreference, setDarkMode, setLightMode, setSystemPreference } = useTheme()
  const [activeTab, setActiveTab] = useState('appearance')

  // UI Preferences state (could be persisted to localStorage)
  const [preferences, setPreferences] = useState(() => {
    const stored = localStorage.getItem('uiPreferences')
    return stored ? JSON.parse(stored) : {
      compactMode: false,
      showTimestamps: true,
      showTypingIndicator: true,
      autoScroll: true,
      soundEffects: false,
      highContrast: false,
      reducedMotion: false,
    }
  })

  const updatePreference = (key, value) => {
    const updated = { ...preferences, [key]: value }
    setPreferences(updated)
    localStorage.setItem('uiPreferences', JSON.stringify(updated))
  }

  if (!isOpen) return null

  const tabs = [
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'preferences', label: 'Preferences', icon: Bell },
    { id: 'shortcuts', label: 'Shortcuts', icon: Keyboard },
  ]

  return (
    <div style={styles.overlay} onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <h2 id="settings-title" style={styles.title}>Settings</h2>
          <button 
            style={styles.closeBtn} 
            onClick={onClose}
            aria-label="Close settings"
            title="Close (Esc)"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div style={styles.content}>
          {/* Sidebar Tabs */}
          <div style={styles.sidebar}>
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  style={styles.tab(activeTab === tab.id)}
                  onClick={() => setActiveTab(tab.id)}
                  aria-pressed={activeTab === tab.id}
                >
                  <Icon size={18} />
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>

          {/* Tab Content */}
          <div style={styles.tabContent}>
            {activeTab === 'appearance' && (
              <AppearanceTab 
                theme={theme}
                isDark={isDark}
                isLight={isLight}
                isSystemPreference={isSystemPreference}
                setDarkMode={setDarkMode}
                setLightMode={setLightMode}
                setSystemPreference={setSystemPreference}
                preferences={preferences}
                updatePreference={updatePreference}
              />
            )}
            {activeTab === 'preferences' && (
              <PreferencesTab 
                preferences={preferences}
                updatePreference={updatePreference}
              />
            )}
            {activeTab === 'shortcuts' && <ShortcutsTab />}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Appearance Tab ───────────────────────────────────────────────────────── */
function AppearanceTab({ 
  theme, 
  isDark, 
  isLight, 
  isSystemPreference, 
  setDarkMode, 
  setLightMode, 
  setSystemPreference,
  preferences,
  updatePreference 
}) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>Theme</h3>
      <p style={styles.sectionDescription}>Choose your preferred color scheme</p>

      <div style={styles.themeGrid}>
        <ThemeOption
          icon={Moon}
          label="Dark"
          description="Easy on the eyes"
          isSelected={isDark && !isSystemPreference}
          onClick={setDarkMode}
          previewStyle={{ background: '#0f1117', borderColor: '#14b8a6' }}
        />
        <ThemeOption
          icon={Sun}
          label="Light"
          description="Clean and bright"
          isSelected={isLight && !isSystemPreference}
          onClick={setLightMode}
          previewStyle={{ background: '#ffffff', borderColor: '#0d9488' }}
        />
        <ThemeOption
          icon={Monitor}
          label="System"
          description="Follows your device"
          isSelected={isSystemPreference}
          onClick={setSystemPreference}
          previewStyle={{ background: 'linear-gradient(135deg, #0f1117 50%, #ffffff 50%)', borderColor: '#64748b' }}
        />
      </div>

      <div style={styles.divider} />

      <h3 style={styles.sectionTitle}>Accessibility</h3>
      
      <ToggleOption
        label="High contrast"
        description="Increase contrast for better visibility"
        isEnabled={preferences.highContrast}
        onToggle={() => updatePreference('highContrast', !preferences.highContrast)}
      />
      
      <ToggleOption
        label="Reduced motion"
        description="Minimize animations throughout the app"
        isEnabled={preferences.reducedMotion}
        onToggle={() => updatePreference('reducedMotion', !preferences.reducedMotion)}
      />
    </div>
  )
}

function ThemeOption({ icon: Icon, label, description, isSelected, onClick, previewStyle }) {
  return (
    <button
      style={styles.themeOption(isSelected)}
      onClick={onClick}
      aria-pressed={isSelected}
    >
      <div style={{ ...styles.themePreview, ...previewStyle }} />
      <div style={styles.themeInfo}>
        <div style={styles.themeLabel}>
          <Icon size={16} />
          <span>{label}</span>
        </div>
        <span style={styles.themeDescription}>{description}</span>
      </div>
      {isSelected && (
        <div style={styles.checkmark}>
          <Check size={14} />
        </div>
      )}
    </button>
  )
}

/* ── Preferences Tab ──────────────────────────────────────────────────────── */
function PreferencesTab({ preferences, updatePreference }) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>Chat Preferences</h3>

      <ToggleOption
        label="Show timestamps"
        description="Display message timestamps on hover"
        isEnabled={preferences.showTimestamps}
        onToggle={() => updatePreference('showTimestamps', !preferences.showTimestamps)}
      />

      <ToggleOption
        label="Auto-scroll"
        description="Automatically scroll to new messages"
        isEnabled={preferences.autoScroll}
        onToggle={() => updatePreference('autoScroll', !preferences.autoScroll)}
      />

      <ToggleOption
        label="Compact mode"
        description="Reduce spacing for a denser layout"
        isEnabled={preferences.compactMode}
        onToggle={() => updatePreference('compactMode', !preferences.compactMode)}
      />

      <div style={styles.divider} />

      <h3 style={styles.sectionTitle}>Notifications</h3>

      <ToggleOption
        label="Sound effects"
        description="Play sounds for important actions"
        isEnabled={preferences.soundEffects}
        onToggle={() => updatePreference('soundEffects', !preferences.soundEffects)}
      />

      <div style={styles.divider} />

      <h3 style={styles.sectionTitle}>Language</h3>
      <p style={styles.sectionDescription}>Select your preferred language</p>
      
      <div style={styles.languageSelector}>
        <Globe size={18} style={{ color: 'var(--text-muted)' }} />
        <select 
          style={styles.select}
          defaultValue="en"
          aria-label="Select language"
        >
          <option value="en">English</option>
          <option value="ar">Arabic (العربية)</option>
          <option value="fr">French (Français)</option>
          <option value="es">Spanish (Español)</option>
          <option value="ur">Urdu (اردو)</option>
        </select>
      </div>
      <p style={styles.comingSoon}>More languages coming soon</p>
    </div>
  )
}

/* ── Shortcuts Tab ────────────────────────────────────────────────────────── */
function ShortcutsTab() {
  const shortcuts = [
    { key: 'Enter', description: 'Send message' },
    { key: 'Shift + Enter', description: 'New line in message' },
    { key: 'Esc', description: 'Close sidebar / modals' },
    { key: 'Ctrl + /', description: 'Open settings' },
    { key: 'Ctrl + N', description: 'New debate session' },
    { key: 'Ctrl + B', description: 'Toggle sidebar' },
  ]

  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>Keyboard Shortcuts</h3>
      <p style={styles.sectionDescription}>Speed up your workflow with these shortcuts</p>

      <div style={styles.shortcutsList}>
        {shortcuts.map(({ key, description }) => (
          <div key={key} style={styles.shortcutItem}>
            <kbd style={styles.kbd}>{key}</kbd>
            <span style={styles.shortcutDescription}>{description}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Toggle Option Component ──────────────────────────────────────────────── */
function ToggleOption({ label, description, isEnabled, onToggle }) {
  return (
    <div style={styles.toggleOption}>
      <div style={styles.toggleInfo}>
        <span style={styles.toggleLabel}>{label}</span>
        <span style={styles.toggleDescription}>{description}</span>
      </div>
      <button
        style={styles.toggleSwitch(isEnabled)}
        onClick={onToggle}
        role="switch"
        aria-checked={isEnabled}
        aria-label={label}
      >
        <span style={styles.toggleThumb(isEnabled)} />
      </button>
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
  },
  modal: {
    background: 'var(--bg-secondary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    width: '100%',
    maxWidth: 640,
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: 'var(--shadow-lg)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-primary)',
  },
  title: {
    color: 'var(--text-primary)',
    fontSize: 18,
    fontWeight: 600,
    margin: 0,
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
  content: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    minHeight: 400,
  },
  sidebar: {
    width: 160,
    borderRight: '1px solid var(--border-primary)',
    padding: '12px 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  tab: (isActive) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 'var(--radius-md)',
    border: 'none',
    background: isActive ? 'var(--accent-dim)' : 'transparent',
    color: isActive ? 'var(--accent-primary)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: isActive ? 500 : 400,
    transition: 'all var(--transition-fast)',
    textAlign: 'left',
  }),
  tabContent: {
    flex: 1,
    padding: '20px',
    overflowY: 'auto',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  sectionTitle: {
    color: 'var(--text-primary)',
    fontSize: 14,
    fontWeight: 600,
    margin: 0,
  },
  sectionDescription: {
    color: 'var(--text-muted)',
    fontSize: 13,
    margin: '-12px 0 0',
  },
  divider: {
    height: 1,
    background: 'var(--border-primary)',
    margin: '8px 0',
  },
  themeGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
    gap: 12,
  },
  themeOption: (isSelected) => ({
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    padding: 12,
    borderRadius: 'var(--radius-lg)',
    border: `2px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-primary)'}`,
    background: 'var(--bg-tertiary)',
    cursor: 'pointer',
    position: 'relative',
    transition: 'all var(--transition-fast)',
  }),
  themePreview: {
    height: 60,
    borderRadius: 'var(--radius-md)',
    border: '2px solid',
  },
  themeInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  themeLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    color: 'var(--text-primary)',
    fontSize: 13,
    fontWeight: 500,
  },
  themeDescription: {
    color: 'var(--text-muted)',
    fontSize: 12,
  },
  checkmark: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 20,
    height: 20,
    borderRadius: 'var(--radius-full)',
    background: 'var(--accent-primary)',
    color: 'var(--bg-primary)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  toggleOption: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
    padding: '12px 0',
  },
  toggleInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  toggleLabel: {
    color: 'var(--text-primary)',
    fontSize: 14,
    fontWeight: 500,
  },
  toggleDescription: {
    color: 'var(--text-muted)',
    fontSize: 12,
  },
  toggleSwitch: (isEnabled) => ({
    width: 44,
    height: 24,
    borderRadius: 'var(--radius-full)',
    background: isEnabled ? 'var(--accent-primary)' : 'var(--border-secondary)',
    border: 'none',
    cursor: 'pointer',
    position: 'relative',
    transition: 'background var(--transition-fast)',
    padding: 2,
  }),
  toggleThumb: (isEnabled) => ({
    width: 20,
    height: 20,
    borderRadius: 'var(--radius-full)',
    background: '#fff',
    transform: isEnabled ? 'translateX(20px)' : 'translateX(0)',
    transition: 'transform var(--transition-fast)',
    boxShadow: 'var(--shadow-sm)',
  }),
  languageSelector: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 14px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-md)',
  },
  select: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: 14,
    cursor: 'pointer',
    outline: 'none',
  },
  comingSoon: {
    color: 'var(--text-muted)',
    fontSize: 12,
    fontStyle: 'italic',
    margin: 0,
  },
  shortcutsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  shortcutItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
    padding: '10px 0',
    borderBottom: '1px solid var(--border-primary)',
  },
  kbd: {
    padding: '6px 10px',
    background: 'var(--bg-tertiary)',
    border: '1px solid var(--border-secondary)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--text-primary)',
    fontSize: 12,
    fontFamily: 'monospace',
    fontWeight: 600,
    minWidth: 80,
    textAlign: 'center',
  },
  shortcutDescription: {
    color: 'var(--text-secondary)',
    fontSize: 14,
  },
}

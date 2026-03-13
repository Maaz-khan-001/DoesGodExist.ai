import { useState } from 'react'
import { Copy, Check, BookOpen } from 'lucide-react'
import CitationPanel from './CitationPanel'

/**
 * IMPROVED MESSAGEBUBBLE
 * 
 * Changes:
 * - Updated to teal accent color
 * - Improved visual hierarchy
 * - Better copy button with icon
 * - Improved citation button styling
 * - Better spacing and typography
 * - Accessibility improvements
 */
export default function MessageBubble({ message, isStreaming = false }) {
  const { role, content, citations = [], isSystemMessage, created_at } = message
  const [citationsOpen, setCitationsOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [hovered, setHovered] = useState(false)

  const streaming = isStreaming || message.isStreaming

  const handleCopy = async () => {
    if (!content) return
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // clipboard not available
    }
  }

  const formattedTime = created_at
    ? new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''

  // ── System message ─────────────────────────────────────────────────────
  if (isSystemMessage || role === 'system') {
    return (
      <div style={styles.systemWrapper} role="alert">
        <div style={styles.systemBubble}>
          <span style={styles.systemIcon}>ℹ️</span>
          <span style={styles.systemText}>{content}</span>
        </div>
      </div>
    )
  }

  // ── User message ───────────────────────────────────────────────────────
  if (role === 'user') {
    return (
      <div style={styles.row('user')}>
        <div style={styles.spacer} />
        <div
          style={styles.userBubble}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          <p style={styles.userText}>{content}</p>
          {hovered && formattedTime && (
            <span style={styles.timestamp('right')}>{formattedTime}</span>
          )}
        </div>
        <div style={styles.avatar('user')} aria-hidden="true">🧑</div>
      </div>
    )
  }

  // ── Assistant message ──────────────────────────────────────────────────
  return (
    <div style={styles.row('assistant')}>
      <div style={styles.avatar('assistant')} aria-hidden="true">🕌</div>
      <div style={styles.assistantOuter}>
        <div
          style={styles.assistantBubble}
          onMouseEnter={() => setHovered(true)}
          onMouseLeave={() => setHovered(false)}
        >
          {/* Content */}
          <AssistantContent content={content} streaming={streaming} />

          {/* Streaming cursor */}
          {streaming && <span style={styles.cursor} aria-hidden="true" />}

          {/* Toolbar (copy + timestamp) */}
          {(hovered || citationsOpen) && !streaming && content && (
            <div style={styles.toolbar}>
              {formattedTime && (
                <span style={styles.timestamp('left')}>{formattedTime}</span>
              )}
              <button
                style={styles.toolbarBtn}
                onClick={handleCopy}
                title={copied ? 'Copied!' : 'Copy to clipboard'}
                aria-label={copied ? 'Copied to clipboard' : 'Copy message'}
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          )}

          {/* Citation toggle */}
          {citations.length > 0 && (
            <div style={styles.citationToggleRow}>
              <button
                style={styles.citationBtn(citationsOpen)}
                onClick={() => setCitationsOpen((o) => !o)}
                aria-expanded={citationsOpen}
                aria-label={`${citations.length} citation sources`}
              >
                <BookOpen size={14} />
                <span>{citations.length} source{citations.length !== 1 ? 's' : ''}</span>
                <span style={styles.chevron(citationsOpen)}>▼</span>
              </button>
            </div>
          )}

          {/* Citation panel */}
          {citationsOpen && <CitationPanel citations={citations} />}
        </div>
      </div>
    </div>
  )
}

/* ── AssistantContent: parses and renders markdown-like text ─────────────── */
function AssistantContent({ content, streaming }) {
  if (!content && streaming) {
    return (
      <div style={styles.thinking}>
        <span style={styles.thinkingDot} />
        <span style={styles.thinkingDot} />
        <span style={styles.thinkingDot} />
        <span style={styles.thinkingText}>Thinking</span>
      </div>
    )
  }

  if (!content) return null

  const lines = content.split('\n')

  return (
    <div style={styles.assistantText}>
      {lines.map((line, i) => {
        // H2 heading
        if (line.startsWith('## ')) {
          return (
            <h3 key={i} style={styles.mdH2}>
              {parseInline(line.slice(3))}
            </h3>
          )
        }
        // H3 heading
        if (line.startsWith('### ')) {
          return (
            <h4 key={i} style={styles.mdH3}>
              {parseInline(line.slice(4))}
            </h4>
          )
        }
        // Horizontal rule
        if (line.trim() === '---' || line.trim() === '***') {
          return <hr key={i} style={styles.mdHr} />
        }
        // Bullet point
        if (line.trimStart().startsWith('- ') || line.trimStart().startsWith('• ')) {
          const text = line.trimStart().slice(2)
          return (
            <p key={i} style={styles.mdBullet}>
              <span style={styles.mdBulletDot}>•</span>
              {parseInline(text)}
            </p>
          )
        }
        // Numbered list
        const numMatch = line.match(/^(\d+)\.\s(.+)/)
        if (numMatch) {
          return (
            <p key={i} style={styles.mdBullet}>
              <span style={styles.mdBulletDot}>{numMatch[1]}.</span>
              {parseInline(numMatch[2])}
            </p>
          )
        }
        // Blockquote
        if (line.startsWith('> ')) {
          return (
            <blockquote key={i} style={styles.mdBlockquote}>
              {parseInline(line.slice(2))}
            </blockquote>
          )
        }
        // Empty line → spacer
        if (line.trim() === '') {
          return <div key={i} style={{ height: 8 }} />
        }
        // Regular paragraph
        return <p key={i} style={styles.mdP}>{parseInline(line)}</p>
      })}
    </div>
  )
}

function parseInline(text) {
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: 'var(--text-primary)' }}>{part.slice(2, -2)}</strong>
    }
    if (part.startsWith('*') && part.endsWith('*')) {
      return <em key={i}>{part.slice(1, -1)}</em>
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} style={styles.inlineCode}>{part.slice(1, -1)}</code>
    }
    return part
  })
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  row: (role) => ({
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
    justifyContent: role === 'user' ? 'flex-end' : 'flex-start',
    marginBottom: 4,
    animation: 'fadeIn var(--transition-fast)',
  }),
  spacer: { flex: 1, minWidth: 40 },
  avatar: (role) => ({
    width: 32,
    height: 32,
    borderRadius: '50%',
    background: role === 'user' ? 'var(--user-bubble)' : 'var(--assistant-bubble)',
    border: '1px solid ' + (role === 'user' ? 'var(--user-bubble-border)' : 'var(--border-primary)'),
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 15,
    flexShrink: 0,
    alignSelf: 'flex-end',
  }),
  userBubble: {
    maxWidth: '72%',
    padding: '12px 16px',
    background: 'var(--user-bubble)',
    border: '1px solid var(--user-bubble-border)',
    borderRadius: '18px 18px 4px 18px',
    position: 'relative',
  },
  userText: {
    color: 'var(--text-primary)',
    fontSize: 15,
    margin: 0,
    whiteSpace: 'pre-wrap',
    lineHeight: 1.6,
    wordBreak: 'break-word',
  },
  assistantOuter: {
    maxWidth: '78%',
    display: 'flex',
    flexDirection: 'column',
  },
  assistantBubble: {
    padding: '14px 18px',
    background: 'var(--assistant-bubble)',
    border: '1px solid var(--border-primary)',
    borderRadius: '18px 18px 18px 4px',
    position: 'relative',
  },
  assistantText: {
    color: 'var(--text-secondary)',
    fontSize: 15,
    lineHeight: 1.7,
  },
  thinking: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '8px 0',
  },
  thinkingDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: 'var(--accent-primary)',
    animation: 'typing 1.4s ease-in-out infinite',
    ':nth-child(2)': { animationDelay: '0.2s' },
    ':nth-child(3)': { animationDelay: '0.4s' },
  },
  thinkingText: {
    color: 'var(--text-muted)',
    fontSize: 14,
    marginLeft: 4,
  },
  mdH2: {
    color: 'var(--accent-primary)',
    fontSize: 16,
    fontWeight: 600,
    margin: '14px 0 8px',
    borderBottom: '1px solid var(--border-primary)',
    paddingBottom: 6,
  },
  mdH3: {
    color: 'var(--accent-secondary)',
    fontSize: 15,
    fontWeight: 600,
    margin: '12px 0 6px',
  },
  mdHr: {
    border: 'none',
    borderTop: '1px solid var(--border-primary)',
    margin: '14px 0',
  },
  mdBullet: {
    display: 'flex',
    gap: 10,
    margin: '4px 0',
    fontSize: 15,
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
  },
  mdBulletDot: {
    color: 'var(--accent-primary)',
    flexShrink: 0,
    minWidth: 20,
    fontWeight: 600,
  },
  mdBlockquote: {
    borderLeft: '3px solid var(--accent-primary)',
    margin: '10px 0',
    paddingLeft: 14,
    color: 'var(--text-muted)',
    fontStyle: 'italic',
  },
  mdP: {
    margin: '4px 0',
    fontSize: 15,
    lineHeight: 1.6,
    color: 'var(--text-secondary)',
  },
  inlineCode: {
    background: 'var(--bg-primary)',
    color: 'var(--accent-primary)',
    padding: '2px 6px',
    borderRadius: 'var(--radius-sm)',
    fontFamily: 'monospace',
    fontSize: 13,
  },
  cursor: {
    display: 'inline-block',
    width: 2,
    height: '1.2em',
    background: 'var(--accent-primary)',
    marginLeft: 3,
    verticalAlign: 'text-bottom',
    animation: 'blink 1s step-end infinite',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 12,
    paddingTop: 10,
    borderTop: '1px solid var(--border-primary)',
  },
  toolbarBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: 'none',
    border: 'none',
    color: 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: 12,
    padding: '4px 8px',
    borderRadius: 'var(--radius-sm)',
    transition: 'all var(--transition-fast)',
  },
  timestamp: (side) => ({
    color: 'var(--text-disabled)',
    fontSize: 11,
    marginLeft: side === 'right' ? 'auto' : 0,
    display: 'block',
    textAlign: side,
  }),
  citationToggleRow: {
    marginTop: 12,
    paddingTop: 10,
    borderTop: '1px solid var(--border-primary)',
  },
  citationBtn: (open) => ({
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: open ? 'var(--accent-dim)' : 'transparent',
    border: 'none',
    color: open ? 'var(--accent-primary)' : 'var(--text-muted)',
    cursor: 'pointer',
    fontSize: 13,
    padding: '6px 10px',
    borderRadius: 'var(--radius-md)',
    fontWeight: open ? 500 : 400,
    transition: 'all var(--transition-fast)',
  }),
  chevron: (open) => ({
    transform: open ? 'rotate(180deg)' : 'rotate(0)',
    transition: 'transform var(--transition-fast)',
    fontSize: 10,
  }),
  systemWrapper: {
    display: 'flex',
    justifyContent: 'center',
  },
  systemBubble: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: 'var(--error-bg)',
    border: '1px solid var(--error)',
    borderRadius: 'var(--radius-full)',
    padding: '8px 16px',
    maxWidth: '80%',
  },
  systemIcon: { fontSize: 14 },
  systemText: { color: 'var(--error)', fontSize: 13 },
}

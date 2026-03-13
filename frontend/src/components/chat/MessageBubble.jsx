import { useState, useRef } from 'react'
import CitationPanel from './CitationPanel'
 
/**
 * MessageBubble
 *
 * Renders a single chat message with full formatting.
 *
 * Props:
 *   message     {object}  — Message object from the store
 *   isStreaming {boolean} — If true, show blinking cursor at end of content
 *
 * Message object shape:
 *   {
 *     id:           string
 *     role:         'user' | 'assistant' | 'system'
 *     content:      string
 *     stage:        string
 *     citations:    array
 *     created_at:   ISO string
 *     isSystemMessage: boolean (optional)
 *     isStreaming:  boolean (optional, alternative to prop)
 *   }
 */
export default function MessageBubble({ message, isStreaming = false }) {
  const { role, content, citations = [], isSystemMessage, created_at } = message
  const [citationsOpen, setCitationsOpen] = useState(false)
  const [copied, setCopied]               = useState(false)
  const [hovered, setHovered]             = useState(false)
 
  const streaming = isStreaming || message.isStreaming
 
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      /* clipboard not available */
    }
  }
 
  const formattedTime = created_at
    ? new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : ''
 
  // ── System message ─────────────────────────────────────────────────────
  if (isSystemMessage || role === 'system') {
    return (
      <div style={styles.systemWrapper}>
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
        <div style={styles.avatar('user')}>🧑</div>
      </div>
    )
  }
 
  // ── Assistant message ──────────────────────────────────────────────────
  return (
    <div style={styles.row('assistant')}>
      <div style={styles.avatar('assistant')}>🕌</div>
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
 
          {/* Toolbar (copy + timestamp) — shown on hover or when citations open */}
          {(hovered || citationsOpen) && !streaming && (
            <div style={styles.toolbar}>
              {formattedTime && (
                <span style={styles.timestamp('left')}>{formattedTime}</span>
              )}
              <button
                style={styles.toolbarBtn}
                onClick={handleCopy}
                title="Copy response"
              >
                {copied ? '✓ Copied' : '⎘ Copy'}
              </button>
            </div>
          )}
 
          {/* Citation toggle */}
          {citations.length > 0 && (
            <div style={styles.citationToggleRow}>
              <button
                style={styles.citationBtn(citationsOpen)}
                onClick={() => setCitationsOpen((o) => !o)}
              >
                📚 {citations.length} source{citations.length !== 1 ? 's' : ''}
                {'  '}{citationsOpen ? '▲' : '▼'}
              </button>
            </div>
          )}
 
          {/* Citation panel */}
          {citationsOpen && (
            <CitationPanel citations={citations} />
          )}
        </div>
      </div>
    </div>
  )
}
 
/* ── AssistantContent: parses and renders markdown-like text ─────────────── */
 
function AssistantContent({ content, streaming }) {
  if (!content && streaming) {
    // Empty content while streaming hasn't started yet
    return <span style={{ color: '#555' }}>Thinking…</span>
  }
 
  // Simple markdown parser
  // Replace with <ReactMarkdown> if you install react-markdown
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
 
/**
 * parseInline: Converts **bold**, *italic*, and `code` to React elements.
 */
function parseInline(text) {
  // Split on bold, italic, code patterns
  const parts = text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} style={{ color: '#e8e9ef' }}>{part.slice(2, -2)}</strong>
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
  }),
  spacer: { flex: 1, minWidth: 40 },
  avatar: (role) => ({
    width: 32,
    height: 32,
    borderRadius: '50%',
    background: role === 'user' ? '#2d5a3d' : '#1e2540',
    border: '1px solid ' + (role === 'user' ? '#3d7a52' : '#2a3560'),
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 15,
    flexShrink: 0,
    alignSelf: 'flex-end',
  }),
  userBubble: {
    maxWidth: '72%',
    padding: '10px 14px',
    background: '#2d5a3d',
    border: '1px solid #3d7a52',
    borderRadius: '18px 18px 4px 18px',
    position: 'relative',
  },
  userText: {
    color: '#e8e9ef',
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
    padding: '12px 16px',
    background: '#1e2130',
    border: '1px solid #2a2d38',
    borderRadius: '18px 18px 18px 4px',
    position: 'relative',
  },
  assistantText: {
    color: '#d4d6e0',
    fontSize: 15,
    lineHeight: 1.7,
  },
  mdH2: {
    color: '#d4a853',
    fontSize: 16,
    fontWeight: 600,
    margin: '12px 0 4px',
    borderBottom: '1px solid #2a2d38',
    paddingBottom: 4,
  },
  mdH3: {
    color: '#c8a44a',
    fontSize: 15,
    fontWeight: 600,
    margin: '10px 0 4px',
  },
  mdHr: {
    border: 'none',
    borderTop: '1px solid #2a2d38',
    margin: '12px 0',
  },
  mdBullet: {
    display: 'flex',
    gap: 8,
    margin: '3px 0',
    fontSize: 15,
    lineHeight: 1.6,
    color: '#d4d6e0',
  },
  mdBulletDot: {
    color: '#d4a853',
    flexShrink: 0,
    minWidth: 18,
    fontWeight: 600,
  },
  mdBlockquote: {
    borderLeft: '3px solid #d4a853',
    margin: '8px 0',
    paddingLeft: 12,
    color: '#8b8fa8',
    fontStyle: 'italic',
  },
  mdP: {
    margin: '3px 0',
    fontSize: 15,
    lineHeight: 1.6,
    color: '#d4d6e0',
  },
  inlineCode: {
    background: '#13151e',
    color: '#d4a853',
    padding: '1px 5px',
    borderRadius: 4,
    fontFamily: 'monospace',
    fontSize: 13,
  },
  cursor: {
    display: 'inline-block',
    width: 2,
    height: '1em',
    background: '#d4a853',
    marginLeft: 2,
    verticalAlign: 'text-bottom',
    animation: 'blink 1s step-end infinite',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 8,
    paddingTop: 6,
    borderTop: '1px solid #2a2d38',
  },
  toolbarBtn: {
    background: 'none',
    border: 'none',
    color: '#555',
    cursor: 'pointer',
    fontSize: 12,
    padding: '2px 6px',
    borderRadius: 4,
  },
  timestamp: (side) => ({
    color: '#444',
    fontSize: 11,
    marginLeft: side === 'right' ? 'auto' : 0,
    display: 'block',
    textAlign: side,
    marginTop: 4,
  }),
  citationToggleRow: {
    marginTop: 8,
    paddingTop: 6,
    borderTop: '1px solid #2a2d38',
  },
  citationBtn: (open) => ({
    background: 'none',
    border: 'none',
    color: open ? '#d4a853' : '#8b8fa8',
    cursor: 'pointer',
    fontSize: 12,
    padding: 0,
    fontWeight: open ? 600 : 400,
  }),
  systemWrapper: {
    display: 'flex',
    justifyContent: 'center',
  },
  systemBubble: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    background: '#1a1520',
    border: '1px solid #3a2a50',
    borderRadius: 20,
    padding: '6px 14px',
    maxWidth: '80%',
  },
  systemIcon: { fontSize: 14 },
  systemText: { color: '#9b8fa8', fontSize: 13 },
}
 
// Inject blink keyframe once
if (typeof document !== 'undefined') {
  const id = 'msg-bubble-styles'
  if (!document.getElementById(id)) {
    const el = document.createElement('style')
    el.id = id
    el.textContent = '@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }'
    document.head.appendChild(el)
  }
}
 
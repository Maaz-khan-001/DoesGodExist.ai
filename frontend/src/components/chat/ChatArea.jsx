import { useRef, useEffect, useState } from 'react'
import useDebateStore from '../../store/debateStore'
import MessageBubble from './MessageBubble'
import { Send, Loader2 } from 'lucide-react'

/**
 * IMPROVED CHATAREA
 * 
 * Changes:
 * - Modern send icon (Paper plane) instead of arrow
 * - Improved input styling with better focus states
 * - Better spacing and responsiveness
 * - Loading state for send button
 * - Character counter with visual feedback
 * - Auto-resize textarea
 * - Accessibility improvements
 */
export default function ChatArea({ onSendMessage, isTyping }) {
  const { messages, currentStage } = useDebateStore()
  const [inputText, setInputText] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [inputText])

  const handleSend = () => {
    const text = inputText.trim()
    if (!text || isTyping) return
    setInputText('')
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    onSendMessage(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const STAGE_LABELS = {
    existence:   'Existence of God',
    prophethood: 'Prophethood',
    muhammad:    'Muhammad ﷺ',
    invitation:  'Invitation to Islam',
  }

  const isNearLimit = inputText.length > 1800
  const isAtLimit = inputText.length >= 2000

  return (
    <div style={styles.container}>
      {/* Stage bar */}
      <div style={styles.stageBar}>
        <span style={styles.stageLabel}>
          <span style={styles.stageIcon}>📖</span>
          {STAGE_LABELS[currentStage] || currentStage}
        </span>
      </div>

      {/* Messages */}
      <div style={styles.messageList} role="log" aria-live="polite" aria-label="Chat messages">
        {messages.length === 0 && (
          <div style={styles.welcome}>
            <div style={styles.welcomeIcon}>☽</div>
            <h2 style={styles.welcomeTitle}>Does God Exist?</h2>
            <p style={styles.welcomeText}>
              Begin with a question, a doubt, or a challenge.
              <br />
              This is a space for honest, open inquiry.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <MessageBubble key={msg.id || idx} message={msg} />
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <MessageBubble
            message={{
              id:        'typing-indicator',
              role:      'assistant',
              content:   '',
              stage:     currentStage,
              citations: [],
              isStreaming: true,
              created_at: new Date().toISOString(),
            }}
            isStreaming
          />
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={styles.inputWrapper}>
        <div 
          style={{
            ...styles.inputArea,
            borderColor: isFocused ? 'var(--accent-primary)' : 'var(--border-primary)',
            boxShadow: isFocused ? '0 0 0 2px var(--accent-glow)' : 'none',
          }}
        >
          <textarea
            ref={textareaRef}
            style={styles.textarea}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="Ask a question, raise a doubt..."
            rows={1}
            maxLength={2000}
            disabled={isTyping}
            aria-label="Message input"
            aria-describedby="char-count"
          />
          <button
            style={styles.sendBtn(isTyping || !inputText.trim())}
            onClick={handleSend}
            disabled={isTyping || !inputText.trim()}
            aria-label={isTyping ? 'Sending message...' : 'Send message'}
            title={isTyping ? 'Sending...' : 'Send message (Enter)'}
          >
            {isTyping ? (
              <Loader2 size={20} style={{ animation: 'spin 1s linear infinite' }} />
            ) : (
              <Send size={20} />
            )}
          </button>
        </div>
        
        {/* Character count */}
        <div 
          id="char-count" 
          style={{
            ...styles.charCount,
            color: isAtLimit ? 'var(--error)' : isNearLimit ? 'var(--warning)' : 'var(--text-disabled)',
          }}
          aria-live="polite"
        >
          {inputText.length}/2000
        </div>
      </div>
    </div>
  )
}

/* ── Styles ───────────────────────────────────────────────────────────────── */
const styles = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-primary)',
    overflow: 'hidden',
  },
  stageBar: {
    padding: '10px 20px',
    background: 'var(--bg-tertiary)',
    borderBottom: '1px solid var(--border-primary)',
    flexShrink: 0,
  },
  stageLabel: {
    color: 'var(--accent-primary)',
    fontSize: 13,
    fontWeight: 500,
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  stageIcon: {
    opacity: 0.8,
  },
  messageList: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  welcome: {
    textAlign: 'center',
    padding: '60px 24px',
    color: 'var(--text-muted)',
    animation: 'fadeIn var(--transition-base)',
  },
  welcomeIcon: {
    fontSize: 48,
    marginBottom: 16,
    opacity: 0.7,
    color: 'var(--accent-primary)',
  },
  welcomeTitle: {
    fontSize: 28,
    color: 'var(--accent-primary)',
    margin: '0 0 12px',
    fontWeight: 700,
  },
  welcomeText: {
    fontSize: 15,
    lineHeight: 1.7,
    maxWidth: 400,
    margin: '0 auto',
  },
  inputWrapper: {
    padding: '12px 16px 8px',
    background: 'var(--bg-tertiary)',
    borderTop: '1px solid var(--border-primary)',
    flexShrink: 0,
  },
  inputArea: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
    padding: '8px 8px 8px 16px',
    background: 'var(--bg-primary)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-xl)',
    transition: 'all var(--transition-fast)',
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    fontSize: 15,
    resize: 'none',
    outline: 'none',
    fontFamily: 'inherit',
    lineHeight: 1.5,
    minHeight: 24,
    maxHeight: 120,
    padding: '4px 0',
  },
  sendBtn: (disabled) => ({
    width: 40,
    height: 40,
    borderRadius: '50%',
    background: disabled ? 'var(--bg-tertiary)' : 'var(--accent-primary)',
    border: 'none',
    color: disabled ? 'var(--text-disabled)' : 'var(--bg-primary)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all var(--transition-fast)',
    transform: disabled ? 'none' : 'scale(1)',
  }),
  charCount: {
    textAlign: 'right',
    fontSize: 11,
    marginTop: 6,
    paddingRight: 8,
    transition: 'color var(--transition-fast)',
  },
}

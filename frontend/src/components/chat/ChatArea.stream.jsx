import { useRef, useEffect, useState, useCallback } from 'react'
import useDebateStore from '../../store/debateStore'
import MessageBubble from './MessageBubble'
import { Send, Loader2, Zap, X } from 'lucide-react'

const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const STREAM_URL   = `${VITE_API_URL}/debate/message/stream/`

/**
 * IMPROVED CHATAREA.STREAM
 * 
 * Changes:
 * - Modern send icon (Paper plane) instead of arrow
 * - Improved input styling with better focus states
 * - Better spacing and responsiveness
 * - Loading state for send button
 * - Character counter with visual feedback
 * - Auto-resize textarea
 * - Better streaming indicator
 * - Accessibility improvements
 */
export default function ChatAreaStream({ onSendMessage, isTyping: _isTyping }) {
  const {
    messages,
    currentSessionId, setCurrentSessionId,
    currentStage, setCurrentStage,
    currentDebateMode,
    addUserMessage,
    addAssistantMessage,
    updateLastMessage,
    prependSession,
    updateSessionInHistory,
  } = useDebateStore()

  const [inputText, setInputText] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [streamingId, setStreamingId] = useState(null)
  const [abortCtrl, setAbortCtrl] = useState(null)
  const [streamError, setStreamError] = useState(null)
  const [isFocused, setIsFocused] = useState(false)
  
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`
    }
  }, [inputText])

  const handleSend = useCallback(async () => {
    const text = inputText.trim()
    if (!text || streaming) return
    setInputText('')
    setStreamError(null)

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // 1. Optimistically add user message to UI
    addUserMessage(text)

    // 2. Add a placeholder assistant message (streaming=true)
    const tempId = `stream-${Date.now()}`
    addAssistantMessage({
      id:         tempId,
      role:       'assistant',
      content:    '',
      stage:      currentStage,
      citations:  [],
      isStreaming: true,
      created_at: new Date().toISOString(),
    })
    setStreamingId(tempId)
    setStreaming(true)

    // 3. Create AbortController so the user can cancel
    const ctrl = new AbortController()
    setAbortCtrl(ctrl)

    try {
      const resp = await fetch(STREAM_URL, {
        method:      'POST',
        credentials: 'include',
        headers:     { 'Content-Type': 'application/json' },
        body:        JSON.stringify({
          message:      text,
          session_id:   currentSessionId || undefined,
          language:     'en',
          debate_mode:  currentDebateMode,
        }),
        signal: ctrl.signal,
      })

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new StreamError(
          errData.error || 'Server error',
          errData.code  || 'SERVER_ERROR',
          resp.status
        )
      }

      // 4. Read SSE stream
      const reader  = resp.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop()

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const raw = line.slice(5).trim()
          if (!raw) continue

          let payload
          try {
            payload = JSON.parse(raw)
          } catch {
            continue
          }

          if (payload.token !== undefined) {
            updateLastMessage((prev) => prev + payload.token)
          }

          if (payload.done) {
            const isNew = !currentSessionId
            setCurrentSessionId(payload.session_id)

            if (payload.stage !== currentStage) {
              setCurrentStage(payload.stage)
            }

            updateLastMessage(
              (prev) => prev,
              {
                id:          tempId,
                isStreaming: false,
                citations:   payload.citations || [],
                stage:       payload.stage,
              }
            )

            if (isNew) {
              prependSession({
                id:           payload.session_id,
                title:        null,
                current_stage: payload.stage,
                debate_mode:  currentDebateMode,
                total_turns:  1,
                created_at:   new Date().toISOString(),
                updated_at:   new Date().toISOString(),
              })
            } else {
              updateSessionInHistory(payload.session_id, {
                current_stage: payload.stage,
                updated_at:   new Date().toISOString(),
              })
            }
          }

          if (payload.error) {
            throw new StreamError(payload.error, payload.code || 'STREAM_ERROR')
          }
        }
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        updateLastMessage(() => '[Response cancelled]', { isStreaming: false })
        return
      }

      const msg = err instanceof StreamError ? err.message : 'Connection error. Please try again.'
      const code = err instanceof StreamError ? err.code : 'NETWORK_ERROR'

      if (code === 'DAILY_LIMIT_REACHED') {
        updateLastMessage(
          () => "You've reached your daily turn limit. Sign up or come back tomorrow.",
          { isStreaming: false, isSystemMessage: true }
        )
      } else {
        updateLastMessage(
          () => `⚠️ ${msg}`,
          { isStreaming: false, isSystemMessage: true }
        )
      }
      setStreamError(msg)

    } finally {
      setStreaming(false)
      setStreamingId(null)
      setAbortCtrl(null)
    }
  }, [
    inputText, streaming, currentSessionId, currentStage, currentDebateMode,
    addUserMessage, addAssistantMessage, updateLastMessage,
    setCurrentSessionId, setCurrentStage, prependSession, updateSessionInHistory,
  ])

  const handleCancel = () => {
    if (abortCtrl) abortCtrl.abort()
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
        {streaming && (
          <span style={styles.streamingBadge}>
            <Zap size={12} />
            Streaming
          </span>
        )}
      </div>

      {/* Message list */}
      <div style={styles.messageList} role="log" aria-live="polite" aria-label="Chat messages">
        {messages.length === 0 && <WelcomeScreen />}

        {messages.map((msg, idx) => (
          <MessageBubble
            key={msg.id || idx}
            message={msg}
            isStreaming={streaming && msg.id === streamingId}
          />
        ))}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
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
            placeholder="Ask a question, raise a doubt, or share your thoughts..."
            rows={1}
            maxLength={2000}
            disabled={streaming}
            aria-label="Message input"
            aria-describedby="stream-char-count"
          />

          {streaming ? (
            <button 
              style={styles.cancelBtn} 
              onClick={handleCancel}
              title="Cancel response"
              aria-label="Cancel streaming response"
            >
              <X size={20} />
            </button>
          ) : (
            <button
              style={styles.sendBtn(!inputText.trim())}
              onClick={handleSend}
              disabled={!inputText.trim()}
              aria-label="Send message"
              title="Send message (Enter)"
            >
              <Send size={20} />
            </button>
          )}
        </div>

        {/* Sub bar */}
        <div style={styles.subBar}>
          <span 
            id="stream-char-count"
            style={{
              ...styles.charCount,
              color: isAtLimit ? 'var(--error)' : isNearLimit ? 'var(--warning)' : 'var(--text-disabled)',
            }}
          >
            {inputText.length}/2000
          </span>
          {streamError && (
            <span style={styles.streamErrorHint} role="alert">
              ⚠️ {streamError}
            </span>
          )}
          {streaming && (
            <span style={styles.streamHint}>
              <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
              Streaming... Press ✕ to cancel
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── WelcomeScreen ───────────────────────────────────────────────────────── */
function WelcomeScreen() {
  return (
    <div style={styles.welcome}>
      <div style={styles.welcomeIcon}>☽</div>
      <h2 style={styles.welcomeTitle}>Does God Exist?</h2>
      <p style={styles.welcomeText}>
        Begin with a question, a doubt, or a challenge.
        <br />
        This is a space for honest, open inquiry.
      </p>
      <div style={styles.welcomeStages}>
        {[
          ['1', 'Existence of God'],
          ['2', 'Prophethood'],
          ['3', 'Muhammad ﷺ'],
          ['4', 'Invitation'],
        ].map(([n, label]) => (
          <div key={n} style={styles.welcomeStage}>
            <span style={styles.welcomeStageNum}>{n}</span>
            <span style={styles.welcomeStageLabel}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Custom error class ──────────────────────────────────────────────────── */
class StreamError extends Error {
  constructor(message, code, status) {
    super(message)
    this.code   = code
    this.status = status
  }
}

/* ── Styles ─────────────────────────────────────────────────────────────── */
const styles = {
  container: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'var(--bg-primary)',
    overflow: 'hidden',
  },
  stageBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
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
  streamingBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    color: 'var(--success)',
    background: 'var(--success-bg)',
    border: '1px solid var(--success)',
    borderRadius: 'var(--radius-full)',
    padding: '4px 10px',
    fontWeight: 500,
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
    padding: '60px 24px 40px',
    color: 'var(--text-muted)',
    animation: 'fadeIn var(--transition-base)',
  },
  welcomeIcon: {
    fontSize: 48,
    color: 'var(--accent-primary)',
    marginBottom: 16,
    opacity: 0.7,
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
    margin: '0 auto 28px',
  },
  welcomeStages: {
    display: 'flex',
    justifyContent: 'center',
    gap: 8,
    flexWrap: 'wrap',
    maxWidth: 420,
    margin: '0 auto',
  },
  welcomeStage: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border-primary)',
    borderRadius: 'var(--radius-md)',
    padding: '8px 14px',
  },
  welcomeStageNum: {
    color: 'var(--accent-primary)',
    fontWeight: 700,
    fontSize: 13,
  },
  welcomeStageLabel: {
    color: 'var(--text-muted)',
    fontSize: 12,
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
  }),
  cancelBtn: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    background: 'var(--error-bg)',
    border: '1px solid var(--error)',
    color: 'var(--error)',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    transition: 'all var(--transition-fast)',
  },
  subBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 6,
    padding: '0 8px',
  },
  charCount: {
    fontSize: 11,
    transition: 'color var(--transition-fast)',
  },
  streamErrorHint: {
    color: 'var(--error)',
    fontSize: 11,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  streamHint: {
    color: 'var(--success)',
    fontSize: 11,
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
}

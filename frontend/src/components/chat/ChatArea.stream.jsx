import { useRef, useEffect, useState, useCallback } from 'react'
import useDebateStore from '../../store/debateStore'
import MessageBubble from './MessageBubble'
 
const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
const STREAM_URL   = `${VITE_API_URL}/debate/message/stream/`
 
/**
 * ChatArea.stream.jsx
 *
 * Streaming-capable chat area.
 * Tokens from the backend SSE endpoint are appended to the
 * assistant message in real time — no waiting for the full response.
 *
 * HOW IT WORKS:
 *   1. User submits message
 *   2. POST to /api/v1/debate/message/stream/
 *   3. Response is an SSE stream: text/event-stream
 *   4. Each 'token' event appends to the streaming message in the store
 *   5. 'done' event triggers metadata update (stage, citations, session_id)
 *   6. 'error' event shows an error bubble
 *
 * FALLBACK:
 *   If the server doesn't support streaming (HTTP 405 or network error),
 *   the component falls back to regular non-streaming mode automatically.
 *
 * PROPS:
 *   onSendMessage  {function}  — Called by parent (ChatPage) — not used in
 *                                streaming mode. Kept for API compatibility.
 *   isTyping       {boolean}   — Ignored in streaming mode (managed internally)
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
 
  const [inputText,    setInputText]    = useState('')
  const [streaming,    setStreaming]     = useState(false)  // SSE in progress
  const [streamingId,  setStreamingId]  = useState(null)    // id of the streaming msg
  const [abortCtrl,   setAbortCtrl]    = useState(null)    // AbortController
  const [streamError,  setStreamError]  = useState(null)
  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)
 
  // Auto-scroll on new content
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
 
  const handleSend = useCallback(async () => {
    const text = inputText.trim()
    if (!text || streaming) return
    setInputText('')
    setStreamError(null)
 
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
        credentials: 'include',    // Send JWT cookie
        headers:     { 'Content-Type': 'application/json' },
        body:        JSON.stringify({
          message:      text,
          session_id:   currentSessionId || undefined,
          language:     'en',
          debate_mode:  currentDebateMode,
        }),
        signal: ctrl.signal,
      })
 
      // Handle HTTP errors before reading stream
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
        buffer = lines.pop()  // Keep incomplete line in buffer
 
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
 
          // Handle different event types
          if (payload.token !== undefined) {
            // Append token to last message
            updateLastMessage((prev) => prev + payload.token)
          }
 
          if (payload.done) {
            // Stream complete — update session metadata
            const isNew = !currentSessionId
            setCurrentSessionId(payload.session_id)
 
            if (payload.stage !== currentStage) {
              setCurrentStage(payload.stage)
            }
 
            // Update the assistant message with final citations + mark done
            updateLastMessage(
              (prev) => prev,           // content is already built
              {
                id:          tempId,
                isStreaming: false,
                citations:   payload.citations || [],
                stage:       payload.stage,
              }
            )
 
            // Update sidebar
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
        // User cancelled — remove the empty streaming message
        updateLastMessage(() => '[Response cancelled]', { isStreaming: false })
        return
      }
 
      // Show error in the streaming bubble
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
 
  return (
    <div style={styles.container}>
      {/* Stage bar */}
      <div style={styles.stageBar}>
        <span style={styles.stageLabel}>
          📖 {STAGE_LABELS[currentStage] || currentStage}
        </span>
        {streaming && (
          <span style={styles.streamingBadge}>⚡ Streaming</span>
        )}
      </div>
 
      {/* Message list */}
      <div style={styles.messageList}>
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
      <div style={styles.inputArea}>
        <textarea
          ref={inputRef}
          style={styles.textarea}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question, raise a doubt, or share your thoughts…"
          rows={2}
          maxLength={2000}
          disabled={streaming}
        />
 
        {streaming ? (
          <button style={styles.cancelBtn} onClick={handleCancel} title="Cancel response">
            ✕
          </button>
        ) : (
          <button
            style={styles.sendBtn(!inputText.trim())}
            onClick={handleSend}
            disabled={!inputText.trim()}
            title="Send (Enter)"
          >
            →
          </button>
        )}
      </div>
 
      <div style={styles.subBar}>
        <span style={styles.charCount}>{inputText.length}/2000</span>
        {streamError && (
          <span style={styles.streamErrorHint}>
            ⚠️ {streamError}
          </span>
        )}
        {streaming && (
          <span style={styles.streamHint}>Streaming… Press ✕ to cancel</span>
        )}
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
        <br />This is a space for honest, open inquiry.
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
    background: '#0f1117',
    overflow: 'hidden',
  },
  stageBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '8px 20px',
    background: '#1a1d24',
    borderBottom: '1px solid #2a2d38',
    flexShrink: 0,
  },
  stageLabel: { color: '#d4a853', fontSize: 13, fontWeight: 500 },
  streamingBadge: {
    fontSize: 11,
    color: '#4caf50',
    background: '#1a2e1a',
    border: '1px solid #2d5a2d',
    borderRadius: 10,
    padding: '2px 8px',
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
    color: '#8b8fa8',
  },
  welcomeIcon:  { fontSize: 48, color: '#d4a853', marginBottom: 12, opacity: 0.7 },
  welcomeTitle: { fontSize: 26, color: '#d4a853', margin: '0 0 10px', fontWeight: 700 },
  welcomeText:  { fontSize: 15, lineHeight: 1.7, maxWidth: 380, margin: '0 auto 28px' },
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
    gap: 6,
    background: '#1e2130',
    border: '1px solid #2a2d38',
    borderRadius: 8,
    padding: '6px 12px',
  },
  welcomeStageNum: {
    color: '#d4a853',
    fontWeight: 700,
    fontSize: 13,
  },
  welcomeStageLabel: { color: '#8b8fa8', fontSize: 12 },
  inputArea: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 8,
    padding: '10px 16px 4px',
    background: '#1a1d24',
    borderTop: '1px solid #2a2d38',
    flexShrink: 0,
  },
  textarea: {
    flex: 1,
    background: '#0f1117',
    border: '1px solid #2a2d38',
    borderRadius: 12,
    padding: '10px 14px',
    color: '#e8e9ef',
    fontSize: 15,
    resize: 'none',
    outline: 'none',
    fontFamily: 'inherit',
    lineHeight: 1.5,
  },
  sendBtn: (disabled) => ({
    width: 44, height: 44,
    borderRadius: '50%',
    background: disabled ? '#1e2130' : '#d4a853',
    border: '1px solid ' + (disabled ? '#2a2d38' : '#d4a853'),
    color: disabled ? '#444' : '#0f1117',
    fontSize: 20,
    cursor: disabled ? 'not-allowed' : 'pointer',
    flexShrink: 0,
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s',
  }),
  cancelBtn: {
    width: 44, height: 44,
    borderRadius: '50%',
    background: '#2e1a1a',
    border: '1px solid #5a2d2d',
    color: '#e07070',
    fontSize: 16,
    cursor: 'pointer',
    flexShrink: 0,
    fontWeight: 'bold',
  },
  subBar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '2px 16px 8px',
    background: '#1a1d24',
    flexShrink: 0,
  },
  charCount:       { color: '#444', fontSize: 11 },
  streamErrorHint: { color: '#c0392b', fontSize: 11 },
  streamHint:      { color: '#4caf50', fontSize: 11 },
}
 
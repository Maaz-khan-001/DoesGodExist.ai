import { useRef, useEffect, useState } from 'react'
import useDebateStore from '../../store/debateStore'
import MessageBubble from './MessageBubble'
 
/**
 * Standard (non-streaming) ChatArea.
 * Renders messages using MessageBubble.
 * All message formatting logic lives in MessageBubble.
 */
export default function ChatArea({ onSendMessage, isTyping }) {
  const { messages, currentStage } = useDebateStore()
  const [inputText, setInputText] = useState('')
  const bottomRef  = useRef(null)
 
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isTyping])
 
  const handleSend = () => {
    const text = inputText.trim()
    if (!text || isTyping) return
    setInputText('')
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
 
  return (
    <div style={styles.container}>
      {/* Stage bar */}
      <div style={styles.stageBar}>
        <span style={styles.stageLabel}>
          📖 {STAGE_LABELS[currentStage] || currentStage}
        </span>
      </div>
 
      {/* Messages */}
      <div style={styles.messageList}>
        {messages.length === 0 && (
          <div style={styles.welcome}>
            <div style={{ fontSize: 40, marginBottom: 12 }}>☽</div>
            <h2 style={styles.welcomeTitle}>Does God Exist?</h2>
            <p style={styles.welcomeText}>
              Begin with a question, a doubt, or a challenge.
            </p>
          </div>
        )}
 
        {messages.map((msg, idx) => (
          <MessageBubble key={msg.id || idx} message={msg} />
        ))}
 
        {/* Typing indicator — rendered as a streaming bubble */}
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
 
      {/* Input */}
      <div style={styles.inputArea}>
        <textarea
          style={styles.textarea}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question, raise a doubt…"
          rows={2}
          maxLength={2000}
          disabled={isTyping}
        />
        <button
          style={styles.sendBtn(isTyping || !inputText.trim())}
          onClick={handleSend}
          disabled={isTyping || !inputText.trim()}
        >
          →
        </button>
      </div>
      <div style={styles.charCount}>{inputText.length}/2000</div>
    </div>
  )
}
 
const styles = {
  container: {
    flex: 1, display: 'flex', flexDirection: 'column',
    background: '#0f1117', overflow: 'hidden',
  },
  stageBar: {
    padding: '8px 20px', background: '#1a1d24',
    borderBottom: '1px solid #2a2d38', flexShrink: 0,
  },
  stageLabel: { color: '#d4a853', fontSize: 13, fontWeight: 500 },
  messageList: {
    flex: 1, overflowY: 'auto',
    padding: '20px 16px',
    display: 'flex', flexDirection: 'column', gap: 12,
  },
  welcome: {
    textAlign: 'center', padding: '60px 24px',
    color: '#8b8fa8',
  },
  welcomeTitle: { fontSize: 24, color: '#d4a853', margin: '0 0 10px' },
  welcomeText:  { fontSize: 15, lineHeight: 1.7, maxWidth: 360, margin: '0 auto' },
  inputArea: {
    display: 'flex', alignItems: 'flex-end', gap: 8,
    padding: '10px 16px 4px',
    background: '#1a1d24', borderTop: '1px solid #2a2d38',
    flexShrink: 0,
  },
  textarea: {
    flex: 1, background: '#0f1117', border: '1px solid #2a2d38',
    borderRadius: 12, padding: '10px 14px', color: '#e8e9ef',
    fontSize: 15, resize: 'none', outline: 'none', fontFamily: 'inherit',
  },
  sendBtn: (disabled) => ({
    width: 44, height: 44, borderRadius: '50%',
    background: disabled ? '#1e2130' : '#d4a853',
    border: '1px solid ' + (disabled ? '#2a2d38' : '#d4a853'),
    color: disabled ? '#444' : '#0f1117',
    fontSize: 20, cursor: disabled ? 'not-allowed' : 'pointer',
    fontWeight: 'bold', flexShrink: 0,
  }),
  charCount: {
    textAlign: 'right', color: '#444', fontSize: 11,
    padding: '2px 16px 8px', background: '#1a1d24',
    flexShrink: 0,
  },
}
 
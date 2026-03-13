import { useState, useCallback } from 'react'
import { useAuth } from '../hooks/useAuth'
import useDebateStore from '../store/debateStore'
import { debateAPI } from '../services/api'
import Navbar          from '../components/layout/Navbar'
import Sidebar         from '../components/layout/Sidebar'
import ChatArea        from '../components/chat/ChatArea'
import ChatAreaStream  from '../components/chat/ChatArea.stream'
 
export default function ChatPage() {
  const { isAuthenticated } = useAuth()
  const {
    currentSessionId, setCurrentSessionId,
    currentStage, setCurrentStage,
    currentDebateMode,
    addUserMessage, addAssistantMessage,
    setTyping, isTyping,
    prependSession, updateSessionInHistory,
    startNewSession,
    streamingEnabled,   // NEW: from store
  } = useDebateStore()
 
  const [sidebarOpen, setSidebarOpen] = useState(false)
 
  /**
   * Standard (non-streaming) sendMessage.
   * Only used when streamingEnabled === false.
   * The streaming ChatArea manages its own fetch internally.
   */
  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isTyping) return
    addUserMessage(text)
    setTyping(true)
 
    try {
      const { data } = await debateAPI.sendMessage({
        message:      text,
        session_id:   currentSessionId || undefined,
        language:     'en',
        debate_mode:  currentDebateMode,
      })
 
      const isNew = !currentSessionId
      setCurrentSessionId(data.session_id)
      if (data.stage !== currentStage) setCurrentStage(data.stage)
 
      addAssistantMessage({
        id:        data.message_id,
        role:      'assistant',
        content:   data.content,
        stage:     data.stage,
        citations: data.citations || [],
        created_at: new Date().toISOString(),
      })
 
      if (isNew && isAuthenticated) {
        prependSession({
          id:            data.session_id,
          title:         null,
          current_stage: data.stage,
          debate_mode:   data.debate_mode,
          total_turns:   data.turn_number,
          created_at:    new Date().toISOString(),
          updated_at:    new Date().toISOString(),
        })
      } else if (isAuthenticated) {
        updateSessionInHistory(data.session_id, {
          current_stage: data.stage,
          total_turns:   data.turn_number,
          updated_at:    new Date().toISOString(),
        })
      }
    } catch (err) {
      const code = err.response?.data?.code
      addAssistantMessage({
        id:            `err-${Date.now()}`,
        role:          'assistant',
        content:       code === 'DAILY_LIMIT_REACHED'
          ? (isAuthenticated
              ? "You've reached your daily turn limit. Please come back tomorrow."
              : "You've used your 5 free turns. Sign up for a free account to continue!")
          : "I'm sorry, something went wrong. Please try again.",
        stage:         currentStage,
        citations:     [],
        created_at:    new Date().toISOString(),
        isSystemMessage: true,
      })
    } finally {
      setTyping(false)
    }
  }, [
    currentSessionId, currentStage, currentDebateMode, isTyping, isAuthenticated,
    addUserMessage, addAssistantMessage, setTyping, setCurrentSessionId,
    setCurrentStage, prependSession, updateSessionInHistory,
  ])
 
  return (
    <div style={styles.container}>
      <Navbar
        onMenuClick={() => setSidebarOpen(true)}
        streamingEnabled={streamingEnabled}  // pass down for toggle UI
      />
      <div style={styles.body}>
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onNewSession={startNewSession}
        />
 
        {/* Switch between streaming and standard ChatArea */}
        {streamingEnabled
          ? (
            <ChatAreaStream
              onSendMessage={sendMessage}  // kept for API compat
              isTyping={isTyping}
            />
          ) : (
            <ChatArea
              onSendMessage={sendMessage}
              isTyping={isTyping}
            />
          )
        }
      </div>
    </div>
  )
}
 
const styles = {
  container: {
    display: 'flex', flexDirection: 'column',
    height: '100vh', background: '#0f1117',
  },
  body: {
    display: 'flex', flex: 1, overflow: 'hidden',
  },
}
 
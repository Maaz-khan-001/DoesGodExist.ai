import { create } from 'zustand'

const useDebateStore = create((set, get) => ({
  // ─── Auth State ──────────────────────────────────────────────────────────
  user: null,
  isAuthLoading: true,
  streamingEnabled: true,
      // FIX: Starts TRUE — prevents flash of login page

  setUser: (user) => set({ user }),
  setAuthLoading: (val) => set({ isAuthLoading: val }),
  isAuthenticated: () => !!get().user,
 
  toggleStreaming: () => set((state) => ({
  streamingEnabled: !state.streamingEnabled
})),
 
setStreamingEnabled: (val) => set({ streamingEnabled: val }),
  // ─── Session State ────────────────────────────────────────────────────────
  currentSessionId: null,
  currentStage: 'existence',
  currentDebateMode: 'standard',
  detectedPersona: null,

  setCurrentSessionId: (id) => set({ currentSessionId: id }),
  setCurrentStage: (stage) => set({ currentStage: stage }),
  setCurrentDebateMode: (mode) => set({ currentDebateMode: mode }),
  setDetectedPersona: (persona) => set({ detectedPersona: persona }),

  // ─── Message State ────────────────────────────────────────────────────────
  messages: [],
  isTyping: false,

  setMessages: (messages) => set({ messages }),

  /**
   * FIX: addUserMessage now accepts EITHER a plain string OR a full message object.
   * Previously it only accepted a string but was called with an object,
   * causing messages to render as "[object Object]".
   */
  addUserMessage: (contentOrObject) => set((state) => {
    const msg = typeof contentOrObject === 'string'
      ? {
          id: `local-${Date.now()}`,
          role: 'user',
          content: contentOrObject,
          stage: state.currentStage,
          citations: [],
          created_at: new Date().toISOString(),
        }
      : contentOrObject  // Already a full message object

    return { messages: [...state.messages, msg] }
  }),

  addAssistantMessage: (msg) => set((state) => ({
    messages: [...state.messages, msg]
  })),

  /**
   * Update the last message in the list (used for streaming responses).
   * Updates only the content field, preserving all other fields.
   */
  updateLastMessage: (contentUpdater, metaUpdates = {}) =>
  set((state) => {
    if (state.messages.length === 0) return state
    const msgs = [...state.messages]
    const last = msgs[msgs.length - 1]
 
    const newContent = typeof contentUpdater === 'function'
      ? contentUpdater(last.content)  // e.g. (prev) => prev + token
      : contentUpdater
 
    msgs[msgs.length - 1] = {
      ...last,
      ...metaUpdates,
      content: newContent,
    }
    return { messages: msgs }
  }),
 

  clearMessages: () => set({ messages: [] }),

  setTyping: (val) => set({ isTyping: val }),

  // ─── Session History (Sidebar) ────────────────────────────────────────────
  sessionHistory: [],  // FIX: Was never loaded from API

  setSessionHistory: (sessions) => set({ sessionHistory: sessions }),

  /**
   * FIX: Prepend new session to sidebar history.
   * Called after the first message creates a new session.
   */
  prependSession: (session) => set((state) => ({
    sessionHistory: [session, ...state.sessionHistory]
  })),

  /**
   * FIX: Update a session in the history list (for title updates, stage changes).
   */
  updateSessionInHistory: (sessionId, updates) => set((state) => ({
    sessionHistory: state.sessionHistory.map((s) =>
      s.id === sessionId ? { ...s, ...updates } : s
    )
  })),

  /**
   * NEW: Remove a session from history (after deletion).
   */
  removeSessionFromHistory: (sessionId) => set((state) => ({
    sessionHistory: state.sessionHistory.filter((s) => s.id !== sessionId)
  })),

  // ─── Full Session Loader ──────────────────────────────────────────────────
  /**
   * FIX: Load a full session into the active chat.
   * Was previously setting messages to session object directly.
   * Now properly extracts session.messages array.
   */
  loadSession: (fullSession) => set({
    currentSessionId: fullSession.id,
    currentStage: fullSession.current_stage,
    currentDebateMode: fullSession.debate_mode,
    detectedPersona: fullSession.detected_persona,
    messages: fullSession.messages || [],
  }),

  // ─── Start a Fresh Session ────────────────────────────────────────────────
  startNewSession: () => set({
    currentSessionId: null,
    currentStage: 'existence',
    currentDebateMode: 'standard',
    detectedPersona: null,
    messages: [],
  }),

  // ─── Full Auth Logout ─────────────────────────────────────────────────────
  logout: () => set({
    user: null,
    currentSessionId: null,
    currentStage: 'existence',
    currentDebateMode: 'standard',
    detectedPersona: null,
    messages: [],
    sessionHistory: [],
    isAuthLoading: false,
  }),
}))

export default useDebateStore

import { useCallback, useEffect } from 'react'
import useDebateStore from '../store/debateStore'
import { authAPI, debateAPI } from '../services/api'

/**
 * useAuth hook
 *
 * Handles:
 *  - Auth initialization on page load (sets isAuthLoading)
 *  - Login / register / logout
 *  - Google OAuth login
 *  - Session history loading after auth
 *
 * FIX: isAuthLoading starts as true and is set to false
 * only after the auth check completes. This eliminates the
 * flash of the login page on page refresh.
 */
export function useAuth() {
  const {
    user, setUser, setAuthLoading, isAuthLoading,
    setSessionHistory, logout: storeLogout,
    isAuthenticated,
  } = useDebateStore()

  // ─── Initialize auth on mount ──────────────────────────────────────────
  const initializeAuth = useCallback(async () => {
    setAuthLoading(true)
    try {
      const { data } = await authAPI.getUser()
      setUser(data)

      // FIX: Load session history after successful auth
      try {
        const { data: sessions } = await debateAPI.getSessions()
        setSessionHistory(Array.isArray(sessions) ? sessions : (sessions.results || []))
      } catch (err) {
        console.warn('Could not load session history:', err)
        setSessionHistory([])
      }
    } catch {
      // Not authenticated — clear user (may have been set previously)
      setUser(null)
      setSessionHistory([])
    } finally {
      // FIX: ALWAYS set loading to false, even on error
      setAuthLoading(false)
    }
  }, [setUser, setAuthLoading, setSessionHistory])

  useEffect(() => {
    initializeAuth()
  }, [])  // Run once on mount

  // ─── Login ─────────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const { data } = await authAPI.login({ email, password })
    // JWT cookie is set by the server automatically
    setUser(data.user)

    // Load session history after login
    try {
      const { data: sessions } = await debateAPI.getSessions()
      setSessionHistory(Array.isArray(sessions) ? sessions : (sessions.results || []))
    } catch {
      setSessionHistory([])
    }

    return data
  }, [setUser, setSessionHistory])

  // ─── Register ──────────────────────────────────────────────────────────
  const register = useCallback(async (email, password1, password2) => {
    const { data } = await authAPI.register({ email, password1, password2 })
    setUser(data.user)
    setSessionHistory([])
    return data
  }, [setUser, setSessionHistory])

  // ─── Google Login ──────────────────────────────────────────────────────
  const googleLogin = useCallback(async (accessToken) => {
    const { data } = await authAPI.googleLogin({ access_token: accessToken })
    setUser(data.user)

    try {
      const { data: sessions } = await debateAPI.getSessions()
      setSessionHistory(Array.isArray(sessions) ? sessions : (sessions.results || []))
    } catch {
      setSessionHistory([])
    }

    return data
  }, [setUser, setSessionHistory])

  // ─── Logout ────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } catch (err) {
      console.warn('Logout API call failed (proceeding with local logout):', err)
    } finally {
      // Always clear local state, even if API call fails
      storeLogout()
    }
  }, [storeLogout])

  return {
    user,
    isAuthLoading,
    isAuthenticated: !!user,
    login,
    register,
    googleLogin,
    logout,
    initializeAuth,
  }
}

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/**
 * Axios instance configured for JWT cookie authentication.
 *
 * FIX: withCredentials: true — sends the httpOnly JWT cookie
 * automatically with every request. No localStorage needed.
 *
 * The JWT access token expires every 15 minutes. When a 401 is received,
 * the interceptor automatically calls /auth/token/refresh/ to get a new
 * access token (using the long-lived refresh cookie).
 */
const api = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,  // FIX: Required for httpOnly JWT cookies
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,  // 60 second timeout (GPT calls can be slow)
})

// Track whether a token refresh is in progress
// Prevents multiple simultaneous refresh attempts
let isRefreshing = false
let failedQueue = []

const processQueue = (error) => {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error)
    else prom.resolve()
  })
  failedQueue = []
}

// ─── Response Interceptor: Auto-refresh on 401 ──────────────────────────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retrying and not the refresh endpoint itself
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/token/refresh/') &&
      !originalRequest.url.includes('/auth/login/')
    ) {
      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => api(originalRequest))
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // Attempt to refresh the access token
        await api.post('/auth/token/refresh/')
        processQueue(null)
        return api(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError)
        // Refresh failed — user needs to log in again
        // Redirect to login without triggering another refresh attempt
        window.location.href = '/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

// ─── Auth API ────────────────────────────────────────────────────────────────
export const authAPI = {
  login: (data) => api.post('/auth/login/', data),
  register: (data) => api.post('/auth/registration/', data),
  logout: () => api.post('/auth/logout/'),
  getUser: () => api.get('/auth/user/'),
  googleLogin: (data) => api.post('/auth/social/google/', data),
  refreshToken: () => api.post('/auth/token/refresh/'),
  requestPasswordReset: (email) => api.post('/auth/password/reset/', { email }),
  confirmPasswordReset: (data) => api.post('/auth/password/reset/confirm/', data),
}

// ─── Debate API ───────────────────────────────────────────────────────────────
export const debateAPI = {
  sendMessage: (data) => api.post('/debate/message/', data),

  getSessions: () => api.get('/debate/sessions/'),

  // FIX: This now returns the full session with messages[]
  getSession: (sessionId) => api.get(`/debate/sessions/${sessionId}/`),

  // NEW: Delete (soft) a session
  deleteSession: (sessionId) => api.delete(`/debate/sessions/${sessionId}/`),
}

// ─── Analytics API (admin) ───────────────────────────────────────────────────
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard/'),
}

export default api


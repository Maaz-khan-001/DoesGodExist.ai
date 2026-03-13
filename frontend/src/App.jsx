import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import ChatPage               from './pages/ChatPage'
import AuthPage               from './pages/AuthPage'
import ForgotPasswordPage     from './pages/ForgotPasswordPage'
import NotFoundPage           from './pages/NotFoundPage'
import LoadingSpinner         from './components/ui/LoadingSpinner'
 
// Lazy-loaded to keep initial bundle small
import { lazy, Suspense } from 'react'
const PasswordResetConfirmPage = lazy(
  () => import('./pages/PasswordResetConfirmPage')
)
 
function ProtectedRoute({ children }) {
  const { isAuthenticated, isAuthLoading } = useAuth()
  if (isAuthLoading) return <LoadingSpinner fullScreen message="Loading…" />
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}
 
function AuthRoute({ children }) {
  const { isAuthenticated, isAuthLoading } = useAuth()
  if (isAuthLoading) return <LoadingSpinner fullScreen message="Loading…" />
  if (isAuthenticated) return <Navigate to="/" replace />
  return children
}
 
export default function App() {
  return (
    <Router>
      <Routes>
 
        {/* Main chat — accessible to everyone including anonymous users */}
        <Route path="/" element={<ChatPage />} />
 
        {/* Auth routes — redirect logged-in users back to chat */}
        <Route path="/login" element={
          <AuthRoute><AuthPage /></AuthRoute>
        } />
 
        {/* NEW: Forgot password */}
        <Route path="/forgot-password" element={
          <AuthRoute><ForgotPasswordPage /></AuthRoute>
        } />
 
        {/* NEW: Password reset confirm (link from email) */}
        <Route path="/password-reset/confirm/:uid/:token" element={
          <Suspense fallback={<LoadingSpinner fullScreen />}>
            <PasswordResetConfirmPage />
          </Suspense>
        } />
 
        {/* CHANGED: 404 page instead of redirect */}
        <Route path="*" element={<NotFoundPage />} />
 
      </Routes>
    </Router>
  )
}
 

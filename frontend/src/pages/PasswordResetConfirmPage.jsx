import { useState } from 'react'
    import { useParams, useNavigate } from 'react-router-dom'
    import { authAPI } from '../services/api'
 
    export default function PasswordResetConfirmPage() {
      const { uid, token } = useParams()
      const navigate = useNavigate()
      const [password1, setPassword1] = useState('')
      const [password2, setPassword2] = useState('')
      const [error, setError] = useState('')
      const [loading, setLoading] = useState(false)
 
      const handleSubmit = async () => {
        if (password1 !== password2) { setError('Passwords do not match.'); return }
        setLoading(true)
        try {
          await authAPI.confirmPasswordReset({ uid, token, new_password1: password1, new_password2: password2 })
          navigate('/login', { state: { message: 'Password reset successfully. Please log in.' } })
        } catch (err) {
          setError(err.response?.data?.error || 'Reset failed. The link may have expired.')
        } finally { setLoading(false) }
      }
      // Render two password inputs + submit button
    }
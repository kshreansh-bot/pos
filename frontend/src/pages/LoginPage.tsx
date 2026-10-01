import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { User } from '../types'
import './LoginPage.css'

interface LoginPageProps {
  onLogin: (user: User) => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await api.login({ username, password })
      onLogin(response.user)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1>Supermarket POS</h1>
        <p className="subtitle">Point of Sale & Inventory System</p>

        {error && <div className="error-alert">{error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              disabled={loading}
            />
          </div>

          <button type="submit" className="btn-primary btn-large" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <div className="credentials-help">
          <p><strong>Demo Credentials:</strong></p>
          <ul>
            <li>Admin: <code>admin</code> / <code>admin123</code></li>
            <li>Manager: <code>manager1</code> / <code>manager123</code></li>
            <li>Cashier: <code>cashier1</code> / <code>cashier123</code></li>
            <li>Inventory: <code>inventory1</code> / <code>inventory123</code></li>
          </ul>
        </div>
      </div>
    </div>
  )
}
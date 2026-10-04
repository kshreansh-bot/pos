import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import POSPage from './pages/POSPage'
import { ReturnsPage } from './pages/ReturnsPage'
import { CustomersPage } from './pages/CustomersPage'
import { ReportsPage } from './pages/ReportsPage'
import { api } from './services/api'
import { User } from './types'
import './App.css'

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check if user is logged in
    if (api.getToken()) {
      api.getCurrentUser()
        .then(setUser)
        .catch(() => {
          api.setToken(null)
          setUser(null)
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  if (loading) {
    return <div className="loading">Loading Supermarket POS...</div>
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" /> : <LoginPage onLogin={setUser} />}
      />
      <Route
        path="/dashboard"
        element={user ? <DashboardPage user={user} onLogout={() => setUser(null)} /> : <Navigate to="/login" />}
      />
      <Route
        path="/pos"
        element={user ? <POSPage user={user} onLogout={() => setUser(null)} /> : <Navigate to="/login" />}
      />
      <Route
        path="/returns"
        element={user ? <ReturnsPage /> : <Navigate to="/login" />}
      />
      <Route
        path="/customers"
        element={user ? <CustomersPage /> : <Navigate to="/login" />}
      />
      <Route
        path="/reports"
        element={user ? <ReportsPage /> : <Navigate to="/login" />}
      />
      <Route path="/" element={<Navigate to={user ? "/dashboard" : "/login"} />} />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  )
}

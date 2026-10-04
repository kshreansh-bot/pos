import { useNavigate } from 'react-router-dom'
import { User } from '../types'
import { api } from '../services/api'
import '../App.css'

interface DashboardPageProps {
  user: User
  onLogout: () => void
}

export default function DashboardPage({ user, onLogout }: DashboardPageProps) {
  const navigate = useNavigate()

  const handleLogout = async () => {
    await api.logout()
    onLogout()
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>Supermarket POS System</h1>
          <div className="user-info">
            <div>
              <p className="font-bold">{user.full_name}</p>
              <p className="text-sm">{user.role.toUpperCase()}</p>
            </div>
            <button onClick={handleLogout} className="btn-secondary">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="main-content">
        <h2>Welcome back, {user.full_name}!</h2>
        <p className="text-muted mt-2">Choose an action below or launch the checkout counter.</p>

        {/* Quick Launch Banner */}
        <div className="card mt-4" style={{ background: '#f0f9ff', borderColor: '#38bdf8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h3 style={{ margin: 0, color: '#0369a1' }}>🛒 POS Billing Terminal (Phase 4 Ready)</h3>
              <p style={{ margin: '0.25rem 0 0 0', color: '#0c4a6e', fontSize: '0.9rem' }}>
                Fast keyboard-driven checkout, barcode scanner, GST calculation, and digital QR receipt generation.
              </p>
            </div>
            <button
              type="button"
              className="btn-primary"
              style={{ padding: '0.75rem 1.5rem', fontSize: '1rem', fontWeight: 700 }}
              onClick={() => navigate('/pos')}
            >
              Open POS Terminal ➔
            </button>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
          <div className="card">
            <h3>Management Tools</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1rem' }}>
              <button className="btn-secondary" onClick={() => navigate('/returns')}>Returns & Cancellations</button>
              <button className="btn-secondary" onClick={() => navigate('/customers')}>Customer & Loyalty</button>
              <button className="btn-secondary" onClick={() => navigate('/reports')}>Store Reports</button>
            </div>
          </div>
          <div className="card">
            <h3>Staff Information</h3>
            <table>
              <tbody>
                <tr>
                  <td><strong>Username:</strong></td>
                  <td>{user.username}</td>
                </tr>
                <tr>
                  <td><strong>Email:</strong></td>
                  <td>{user.email || 'N/A'}</td>
                </tr>
                <tr>
                  <td><strong>Role:</strong></td>
                  <td><span style={{ background: '#e0f2fe', color: '#0369a1', padding: '0.1rem 0.4rem', borderRadius: '4px', fontWeight: 600 }}>{user.role}</span></td>
                </tr>
                <tr>
                  <td><strong>Max Discount Limit:</strong></td>
                  <td><strong>{user.max_discount_percent}%</strong></td>
                </tr>
                <tr>
                  <td><strong>Terminal Status:</strong></td>
                  <td>{user.is_active ? '🟢 Active' : '🔴 Inactive'}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>System Status</h3>
            <ul style={{ marginLeft: '1.5rem', marginTop: '0.5rem', lineHeight: '1.8' }}>
              <li>✅ <strong>Phase 1:</strong> Foundation</li>
              <li>✅ <strong>Phase 2:</strong> Inventory Engine</li>
              <li>✅ <strong>Phase 3:</strong> Billing Engine</li>
              <li>✅ <strong>Phase 4:</strong> POS UI</li>
              <li>✅ <strong>Phase 5:</strong> Customer Loyalty & Returns</li>
              <li>✅ <strong>Phase 6:</strong> Reports & Demo Seeder</li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  )
}
